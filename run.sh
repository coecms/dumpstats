#!/bin/bash

# Ensure correct modules loaded
module purge
module load git/2.37.3
#module use /g/data/hh5/public/modules
#module load conda

eval "$(/g/data/hh5/public/apps/miniconda3/bin/conda shell.bash hook)"

conda activate "${CONDA_PREFIX}"/envs/cms/stats

# Get latest version of config.yaml
git pull

# Run doit with the default dodo.py script. Use a bunch
# of threads to speed it up. Select just the dump_SU and
# dump_storage tasks
doit -n 4 -P thread dump_SU dump_lquota dump_storage

# Split the upload into a separate call using a single thread
# doit start_tunnel upload_storage upload_usage
doit start_tunnel upload_usage upload_lquota upload_storage
