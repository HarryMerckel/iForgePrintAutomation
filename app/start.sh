#!/bin/bash

if [ ! -d "/data/mysql" ]; then
    rsync -avzh /var/lib/mysql/ /data
fi

echo "datadir=/data" >> /etc/mysql/my.cnf

/etc/init.d/mysql start

python3 httpserver.py &
python3 Supervisor.py