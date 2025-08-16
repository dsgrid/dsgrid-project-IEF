#!/bin/bash
set -e
dsgrid_cli="dsgrid-cli.py"
abspath_dsgrid_cli="$(which dsgrid-cli.py)"
new_args=()

for arg in "$@"; do
    if [[ "$arg" == "$dsgrid_cli" ]]; then
        new_args+=("$abspath_dsgrid_cli")
    elif [[ "$arg" == "spark-submit" ]]; then
        new_args+=("$arg")
	new_args+=("--master=spark://$(hostname):7077")
    else
        new_args+=("$arg")
    fi
done

# Keep synced with star_spark_cluster.sh
work_dir=$(pwd)/$(hostname)
export SPARK_CONF_DIR=${work_dir}/conf
module load python
source ~/python-envs/dsgrid/bin/activate
${new_args[@]}
