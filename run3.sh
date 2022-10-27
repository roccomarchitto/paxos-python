#!/bin/bash
pkill -f python 2>/dev/null

# Update hosts.txt (must match consensus drivers list below this section)
echo "PROPOSERS 1" > hosts.txt
echo "ACCEPTORS 3" >> hosts.txt
echo "LEARNERS 1" >> hosts.txt # Recall last con is always a learner, so learners must be >= 1
echo "localhost 10000 con" >> hosts.txt
echo "localhost 10001 con" >> hosts.txt
echo "localhost 10002 con" >> hosts.txt
echo "localhost 10003 con" >> hosts.txt
echo "localhost 10004 con" >> hosts.txt
# Add the clients below
echo "localhost 10005 cli" >> hosts.txt
echo "localhost 10006 cli" >> hosts.txt
echo "localhost 10007 cli" >> hosts.txt
echo "localhost 10008 cli" >> hosts.txt

#############################################################

# Launch all consensus drivers (must match hosts.txt)
# Argument format is [UID] [IS_LAST_NODE]
# UIDs must be from 0 to n-1

python3 condriver.py 0 &
python3 condriver.py 1 &
python3 condriver.py 2 &
python3 condriver.py 3 &
python3 condriver.py 4 &

# Launch all client drivers
# Note that proposers cannot be determined here since they are decided amongst the processes themselves during runtime
# Argument format is [UID] [V] where V is the value the client wants to assign the global variable
#                       P is the desired proposer index, which is calculated modulo the length of proposers

python3 clidriver.py 5 55 1 &
python3 clidriver.py 6 56 1 &
python3 clidriver.py 7 57 1 &
python3 clidriver.py 8 230 1 &