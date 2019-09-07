#!/bin/bash

/etc/init.d/mysql start

python3 httpserver.py &
python3 Supervisor.py
sleep 10m