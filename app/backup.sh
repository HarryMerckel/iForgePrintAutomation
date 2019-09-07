#!/bin/bash

set -o errexit
set -o nounset

if [ "$#" -ne "1" ]; then
  echo "Expected 1 arguments, got $#" >&2
  exit 2
fi

mysqldump queue --single-transaction --user=root --password=${1} > /data/queue_backup.sql