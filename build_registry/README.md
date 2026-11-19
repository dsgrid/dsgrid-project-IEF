# NLR HPC Run Notes

*These notes assume that you are also following along with the dsgrid "How to Start a Spark Cluster on Kestrel"*

Obtain two nodes:

```
salloc -t XX:00:00 -N2 --tmp=1600G --mem=240G
```

and `cd` into your working directory.

If this directory has been used before, save the previous run statistics first.
`sparkctl configure` recreates `conf/` (deleting `conf/events`), and restarting
the resource monitor resets `stats-output/`:

```
cp -r conf/events runs/events_$(date +%F_%H%M)
cp -r stats-output runs/stats_$(date +%F_%H%M)
```

Configure and start spark (default executor resources and shuffle partitions are
sufficient for this step; `--local-storage` puts shuffle data on node-local NVMe):

```
sparkctl configure --local-storage --history-server --resource-monitor --metrics-csv
sparkctl start
```

Confirm the master is up and all workers have registered before submitting.
Startup can take several minutes when the shared filesystem is slow.

```
curl -s http://$(hostname):8080/json/ | grep -E '"status"|"aliveworkers"'
```

To capture resource usage statistics:

```
/usr/bin/time -v -o runs/<component>_<step>.time \
  spark-submit --master=spark://$(hostname):7077 $(which dsgrid-cli.py) \
  -l runs/<component>_<step>.log \
  registry ...
```

`-l` appends to an existing log, but `-o` overwrites the `.time` file, so use a
new `<step>` name (e.g., `transport_submit2`) when re-running a step.

When finished:

```
sparkctl stop
```
