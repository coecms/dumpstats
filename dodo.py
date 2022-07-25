import time

import glob
import os
import psutil
import shlex
import socket
import subprocess
import yaml

def write_header(filename):
    with open(filename, 'w') as fh:
      print("%%%%%%%%%%%%%%%%", file=fh)
      print("{date}".format(date=makedatestamp('%a %b %d %H:%M:%S %Z %Y')), file=fh)

def run_stats_cmd_gen(config):
    """
    Generate an action dict to run a generic stats command
    """
    actions = []
    if config.get('write_header', False):
      actions.append( ( write_header, [config['outfile']] ))

    actions.append( "{cmd} {options} >> {outfile}".format(**config) )

    job_dict = {
        'doc': 'Run {cmd} and dump to file'.format(**config),
        'name': config['name'],
        'actions': actions,
        'verbosity': 2,
    }
    if config.get('task_dep',False):
      job_dict['task_dep'] = config['task_dep']
    if config.get('file_dep',False):
      job_dict['file_dep'] = config['file_dep']

    return job_dict

def read_config(filename):
    """
    Return a configuration dictionary
    """
    with open(filename, 'r') as config_file:
        return yaml.safe_load(config_file)

def mkdir(path):
    """
    Robust make directory, ignores if already exists
    """
    try:
        os.makedirs(path)
    except FileExistsError:
        pass

env = os.environ

DOIT_CONFIG = {'action_string_formatting': 'both'}

global_config = read_config('config.yaml')

def makedatestamp(format='%F'):
  return time.strftime(format)

stamp = makedatestamp(global_config['defaults']['dateformat'])
outputdir = global_config['defaults']['outputdir']
mkdir(outputdir)

def task_dump_SU():
  """
  Loop over all compute projects in the global config and create a 
  separate task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """
  for project in global_config['compute']:
    outfile = '{stamp}.{project}.SU.dump'.format(stamp=stamp, project=project)
    config = {
      'cmd': 'nci_account_json',
      'write_header': True,
      'name': '{project}_SU'.format(project=project),
      'outfile': os.path.join(outputdir,outfile),
      'options': '-P {project}'.format(project=project),
    }
    yield run_stats_cmd_gen(config)

def task_dump_lquota():
  """
  Dump lquota data until reporting tools are fixed
  """
  outfile = '{stamp}.lquota.dump'.format(stamp=stamp)
  config = {
    'cmd': 'lquota',
    'write_header': True,
    'name': 'lquota',
    'outfile': os.path.join(outputdir,outfile),
    'options': ''
  }
  yield run_stats_cmd_gen(config)

def task_dump_storage():
  """
  Loop over all mount points in the global config and create a 
  separate task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """
  for mount, projects in global_config['mounts'].items():
    if mount == 'scratch':
      # scratch accounting is by contents of a /scratch/project directory, not group ownership of files
      project_option = '--project'
    else:
      project_option = '--group'

    for project in projects:
      outfile = '{stamp}.{project}.{mount}.dump'.format(stamp=stamp, project=project, mount=mount)
      print(mount, project, outfile)
      config = {
        'cmd': 'nci-files-report'.format(mount=mount),
        'write_header': True,
        'name': '{project}_{mount}'.format(project=project, mount=mount),
        'outfile': os.path.join(outputdir,outfile),
        'options': '{option} {project} --filesystem {mount}'.format(option=project_option, project=project, mount=mount),
      }
      yield run_stats_cmd_gen(config)


def task__listing():
  """
  Hidden test task that just runs ls
  """
  return {
    'doc': 'test action: directory listing',
    'actions': ['ls'],
    'verbosity': 2,
  }

# Global variable so we can update and access in multiple tasks
server = None

def poll_port(host, port):
  """
  Poll a port and only return when port is open
  """
  result = -1
  while result != 0:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host,port))
    sock.close()

def start_server():
  global server
  server = subprocess.Popen(
    shlex.split('ssh -N -L '
                '{local_port}:localhost:{remote_port} '
                '{remote_host}'.format(
                **global_config['defaults']))
  )
  poll_port('localhost', global_config['defaults']['local_port'])
  
def stop_server():
  global server
  server.kill()
  server.wait()
  
def task_start_tunnel():
  """
  Open a tunnel to access the postgres DB on the jenkins VM
  The teardown action ensures the tunnel is closed when all
  tasks are finished
  """
  return {
    'actions': [ start_server ],
    'teardown': [ stop_server ]
  }
  return True

def task_upload_usage():
  """
  Loop over all compute projects in the global config and create a 
  separate task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """

  for dumpfile in glob.glob(os.path.join(outputdir,'*.SU.dump')):
    stamp, project = os.path.basename(dumpfile).split('.')[:2]
    # Grab the project code from the file
    outfile = '{project}.SU.upload.log'.format(project=project)
    dburl = global_config['defaults'].get('dburl','postgresql://localhost:{local_port}/grafana').format(**global_config['defaults'])
    config = {
      'cmd': 'parse_account_usage_data',
      'name': '{project}_SU_upload_{datestamp}'.format(project=project, datestamp=stamp),
      'outfile': os.path.join(outputdir,outfile),
      'options': '-db {dburl} {file}'.format(dburl=dburl, file=dumpfile),
      # 'task_dep': [ 'dump_SU:{project}_SU'.format(project=project), 'start_tunnel' ],
      # 'task_dep': [ 'start_tunnel' ],
      # 'file_dep': [ dumpfile ],
    }
    yield run_stats_cmd_gen(config)

def task_upload_storage():
  """
  Loop over all mounts the global config, find all dumpfiles and create 
  a separate sub-task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """
  for mount in global_config['mounts']:
    for dumpfile in glob.glob(os.path.join(outputdir,'*.{mount}.dump'.format(mount=mount))):
      stamp, project = os.path.basename(dumpfile).split('.')[:2]
      outfile = '{project}.storage.upload.log'.format(project=project)
      dburl = global_config['defaults'].get('dburl','postgresql://localhost:{local_port}/grafana').format(**global_config['defaults'])
      config = {
        'cmd': 'parse_user_storage_data',
        'name': '{project}_{mount}_upload_{datestamp}'.format(project=project, mount=mount, datestamp=stamp),
        'outfile': os.path.join(outputdir,outfile),
        'options': '-db {dburl} {file}'.format(dburl=dburl, file=dumpfile),
        # 'task_dep': [ 'dump_storage:{project}_{mount}'.format(project=project, mount=mount), 'start_tunnel'],
        # 'task_dep': [ 'start_tunnel' ],
        # 'file_dep': [ dumpfile ],
      }
      yield run_stats_cmd_gen(config)

def task_upload_lquota():
  """
  Loop over all mounts the global config, find all dumpfiles and create 
  a separate sub-task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """
  for dumpfile in glob.glob(os.path.join(outputdir,'*.lquota.dump')):
    stamp = os.path.basename(dumpfile).split('.')[0]
    outfile = 'lquota.storage.upload.log'
    dburl = global_config['defaults'].get('dburl','postgresql://localhost:{local_port}/grafana').format(**global_config['defaults'])
    config = {
      'cmd': 'parse_lquota_data',
      'name': 'lquota_upload_{datestamp}'.format(datestamp=stamp),
      'outfile': os.path.join(outputdir,outfile),
      'options': '-db {dburl} {file}'.format(dburl=dburl, file=dumpfile),
      # 'task_dep': [ 'dump_storage:{project}_{mount}'.format(project=project, mount=mount), 'start_tunnel'],
      # 'task_dep': [ 'start_tunnel' ],
      # 'file_dep': [ dumpfile ],
    }
    yield run_stats_cmd_gen(config)