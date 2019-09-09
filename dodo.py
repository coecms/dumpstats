from datetime import datetime
import os
import yaml

def run_stats_cmd_gen(config):
    """
    Generate an action dict to run a generic stats command
    """
    action = "{cmd} {options} {project} > {outfile}".format(**config)

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

def task_dump_all():

  stamp = makedatestamp(global_config['defaults']['dateformat'])

  mkdir(global_config['defaults']['outputdir'])

  for project in global_config['compute']:
    outfile = '{stamp}.{project}.SU.dump'.format(stamp=stamp, project=project)
    config = {
      'project': project,
      'cmd': 'nci_account',
      'name': '{project}_SU'.format(project=project),
      'outfile': os.path.join(global_config['defaults']['outputdir'],outfile),
      'options': '-vv -P',
    }
    yield run_stats_cmd_gen(config)

  for mount, projects in global_config['mounts'].items():
    for project in projects:
      outfile = '{stamp}.{project}.{mount}.dump'.format(stamp=stamp, project=project, mount=mount)
      config = {
        'project': project,
        'cmd': '{mount}_files_report'.format(mount=mount),
        'name': '{project}_{mount}'.format(project=project, mount=mount),
        'outfile': os.path.join(global_config['defaults']['outputdir'],outfile),
        'options': '-G',
      }
      yield run_stats_cmd_gen(config)
