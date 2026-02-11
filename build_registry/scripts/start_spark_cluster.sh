#!/bin/bash
# Allow multiple compute nodes to work from the same base directory.
# Keep synced with spark_submit_wrapper.sh
work_dir=$(pwd)/$(hostname)
mkdir -p ${work_dir}
configure_and_start_spark.sh \
    --directory ${work_dir} \
    --spark-scratch ${work_dir}/scratch \
    --partition-multiplier 4 \
    --hive-metastore \
    --metastore-dir ${work_dir} \
    --postgres-hive-metastore \
    --thrift-server
