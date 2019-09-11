import time

import glob
import os
import shlex
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

    return {
        'doc': 'Run {cmd} and dump to file'.format(**config),
        'name': config['name'],
        'actions': actions,
        'verbosity': 2,
    }

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

# Read the config inside the task so that it is the version after 
# the git pull task
global_config = read_config('config.yaml')

def makedatestamp(format='%F'):
  return time.strftime(format)

stamp = makedatestamp(global_config['defaults']['dateformat'])
mkdir(global_config['defaults']['outputdir'])

def task_dump_SU():
  """
  Loop over all compute projects in the global config and create a 
  separate task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """
  for project in global_config['compute']:
    outfile = '{stamp}.{project}.SU.dump'.format(stamp=stamp, project=project)
    config = {
      'cmd': 'nci_account',
      'write_header': True,
      'name': '{project}_SU'.format(project=project),
      'outfile': os.path.join(global_config['defaults']['outputdir'],outfile),
      'options': '-vv -P {project}'.format(project=project),
    }
    yield run_stats_cmd_gen(config)

def task_dump_storage():
  """
  Loop over all mount points in the global config and create a 
  separate task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """
  for mount, projects in global_config['mounts'].items():
    for project in projects:
      outfile = '{stamp}.{project}.{mount}.dump'.format(stamp=stamp, project=project, mount=mount)
      config = {
        'cmd': '{mount}_files_report'.format(mount=mount),
        'write_header': True,
        'name': '{project}_{mount}'.format(project=project, mount=mount),
        'outfile': os.path.join(global_config['defaults']['outputdir'],outfile),
        'options': '-G {project}'.format(project=project),
      }
      yield run_stats_cmd_gen(config)


def task_listing():
  return {
    'actions': ['ls'],
    'verbosity': 2,
  }

# Global variable so we can update and access in multiple tasks
server = None

remote_host = 'jenkins'
remote_port = 5432
local_port = 9107

def start_server():
  global server

  server = subprocess.Popen(
    shlex.split('ssh -NL {local_port}:localhost:{remote_port} {remote_host}'.format(
      local_port=local_port,
      remote_port=remote_port,
      remote_host=remote_host,
      )
    )
  )
  
def stop_server():
  global server
  return server.kill()
  
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

  dumpfiles = glob.glob(os.path.join(global_config['defaults']['outputdir'],'*.SU.dump'))

  for file in dumpfiles:
    # Grab the project code from the file
    datestamp, project = os.path.basename(file).split('.')[:2]
    outfile = '{project}.SU.upload.log'.format(project=project)
    config = {
      'cmd': 'parse_account_usage_data',
      'name': '{project}_SU_upload_{datestamp}'.format(project=project, datestamp=datestamp),
      'outfile': os.path.join(global_config['defaults']['outputdir'],outfile),
      'options': '-db postgresql://localhost:{port}/grafana {file}'.format(port=local_port,file=file),
      'task_dep': ['start_tunnel'],
    }
    yield run_stats_cmd_gen(config)

def task_upload_storage():
  """
  Loop over all compute projects in the global config and create a 
  separate task for each by yielding a run dictionary. doit will 
  generate all the tasks first, and then run them all.
  """

  dumpfiles = []
  for mount in global_config['mounts']:
    dumpfiles.extend(glob.glob(os.path.join(global_config['defaults']['outputdir'],'*.{mount}.dump'.format(mount=mount))))

  for file in dumpfiles:
    # Grab the project code from the file
    datestamp, project, mount = os.path.basename(file).split('.')[:3]
    outfile = '{project}.SU.upload.log'.format(project=project)
    config = {
      'cmd': 'parse_account_usage_data',
      'name': '{project}_{mount}_upload_{datestamp}'.format(project=project, mount=mount, datestamp=datestamp),
      'outfile': os.path.join(global_config['defaults']['outputdir'],outfile),
      'options': '-db postgresql://localhost:{port}/grafana {file}'.format(port=local_port,file=file),
      'task_dep': ['start_tunnel'],
    }
    yield run_stats_cmd_gen(config)