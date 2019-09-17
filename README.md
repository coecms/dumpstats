# Dumpstats

This script uses [doit](https://pydoit.org]) to call system accounting scripts
which dump system usage data to text dumpfiles, which are later processed and
the data added to the postgresql DB backend for grafana

To dump all relevant stats:
```
doit
```

The jenkins jobs runs a script, `run.sh`. This loads a bespoke `conda` environment,
makes sure the code and config is up to date and then runs the dump separately from
the upload step. The dump step is
```
doit -n 64 -P thread dump_SU dump_storage
```
which utilises 64 threads (many more than needed) to run all the dump routines in
parallel for speed.

Then the upload tasks are run separately and serially afterwards:
```
doit start_tunnel upload_storage upload_usage
```
There were issues running this in parallel, which there shouldn't be, but it wasn't 
worth wasting time to try and fix.

It is possible to select a subset of jobs to run, e.g.
```
doit dump_all:w35_SU
.  dump_SU:w35_SU
```
wildcards will also work
```
$ doit dump_SU:w40_*
.  dump_all:w40_SU
.  dump_all:w40_short
.  dump_all:w40_gdata1a

$ doit dump_storage:*_gdata3
.  dump_all:w42_gdata3
.  dump_all:w48_gdata3
.  dump_all:w97_gdata3
.  dump_all:hh5_gdata3
.  dump_all:w28_gdata3
```

The script will pull the latest version of the code before running, so changing
the project codes in `config.yaml` will change the statistics being dumped.

The `config.yaml` format should be straightforward. The `defaults` section sets
some global defaults:
```yaml
defaults:
  outputdir: /g/data3/hh5/admin/analytics/logs
  dateformat: '%F'
  remote_host: jenkins
  remote_port: 5432
  local_port: 9107
  dburl: postgresql://localhost:{local_port}/grafana
```
Note that `dburl` is a python format string and the key/value pairs in the `defaults` 
dictionary are passed to the `format` statement, so the value of `local_port` is
substituted into the `dburl` value, as well as being used in the ssh tunnel command.
