#!/bin/bash
pkill -f python 2>/dev/null

echo "PROPOSERS 1" > hosts.txt
echo "ACCEPTORS 1" >> hosts.txt
echo "LEARNERS 1" >> hosts.txt

echo "localhost 10000 con" >> hosts.txt
echo "localhost 10001 con" >> hosts.txt
echo "localhost 10002 con" >> hosts.txt

echo "localhost 10003 cli" >> hosts.txt

python3 condriver.py 0 &
python3 condriver.py 1 &
python3 condriver.py 2 &

python3 clidriver.py 3 210 0 &