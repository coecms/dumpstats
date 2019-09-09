#!/bin/bash

# Ensure correct modules loaded
module purge
module use /g/data3/hh5/public/modules
module load conda/analysis3-unstable

# Run doit with the default dodo.py script. Use a bunch
# of threads to speed it up
doit -n 64 -P thread