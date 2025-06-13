#!/bin/bash
configure_and_start_spark.sh \
    --spark-scratch $(pwd)/scratch \
    --partition-multiplier 4 \
    --hive-metastore \
    --postgres-hive-metastore \
    --thrift-server
