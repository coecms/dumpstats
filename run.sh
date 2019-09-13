#!/bin/bash

# Ensure correct modules loaded
module purge
module use /g/data3/hh5/public/modules
module load conda
conda activate stats

# Get latest version of config.yaml
git pull

# Run doit with the default dodo.py script. Use a bunch
# of threads to speed it up. Select just the dump_SU and
# dump_storage tasks
doit -n 64 -P thread dump_SU dump_storage start_tunnel upload_storage upload_usage
