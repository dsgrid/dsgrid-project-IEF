#!/bin/bash
set -e
module load python
source ~/python-envs/dsgrid/bin/activate
$@
