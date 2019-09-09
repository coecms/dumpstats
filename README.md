# Dumpstats

This script uses [doit](https://pydoit.org]) to call system accounting scripts
which dump system usage data to text dumpfiles, which are later processed and
the data added to the postgresql DB backend for grafana

To dump all relevant stats:
```
doit
```

To make it run a little faster specify a larger number of threads
```
doit -n 64 -P thread
```
This is the command that is run automatically by Jenkins.

This should result in a `dumpdir` directory with a number of dump files 
contained therein.

It is possible to select a subset of jobs to run, e.g.
```
doit dump_all:w35_SU
.  dump_all:w35_SU
```
wildcards will also work
```
$ doit dump_all:w40_*
.  dump_all:w40_SU
.  dump_all:w40_short
.  dump_all:w40_gdata1a

$ doit dump_all:*_gdata3
.  dump_all:w42_gdata3
.  dump_all:w48_gdata3
.  dump_all:w97_gdata3
.  dump_all:hh5_gdata3
.  dump_all:w28_gdata3
```

The script will pull the latest version of the code before running, so changing
the project codes in `config.yaml` will change the statistics being dumped.
