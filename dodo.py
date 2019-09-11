from datetime import datetime
import os
import yaml

def run_stats_cmd_gen(config):
    """
    Generate an action dict to run a generic stats command
    """
    action = "{cmd} {options} > {outfile}".format(**config)

    return {
        'doc': 'Run {cmd} and dump to file'.format(**config),
        'name': config['name'],
        'actions': [action],
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

global_config = read_config('config.yaml')

def makedatestamp(format='%F'):
  return datetime.now().strftime(format)

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
        'name': '{project}_{mount}'.format(project=project, mount=mount),
        'outfile': os.path.join(global_config['defaults']['outputdir'],outfile),
        'options': '-G {project}'.format(project=project),
      }
      yield run_stats_cmd_gen(config)