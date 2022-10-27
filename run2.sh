#!/bin/bash
pkill -f python 2>/dev/null

# Update hosts.txt (must match consensus drivers list below this section)
echo "PROPOSERS 3" > hosts.txt
echo "ACCEPTORS 3" >> hosts.txt
echo "LEARNERS 5" >> hosts.txt # Recall last con is always a learner, so learners must be >= 1
echo "localhost 10000 con" >> hosts.txt
echo "localhost 10001 con" >> hosts.txt
echo "localhost 10002 con" >> hosts.txt
echo "localhost 10003 con" >> hosts.txt
echo "localhost 10004 con" >> hosts.txt
echo "localhost 10005 con" >> hosts.txt
echo "localhost 10006 con" >> hosts.txt
echo "localhost 10007 con" >> hosts.txt
echo "localhost 10008 con" >> hosts.txt
echo "localhost 10009 con" >> hosts.txt
echo "localhost 10010 con" >> hosts.txt
# Add the clients below
echo "localhost 10011 cli" >> hosts.txt
echo "localhost 10012 cli" >> hosts.txt
echo "localhost 10013 cli" >> hosts.txt
echo "localhost 10014 cli" >> hosts.txt
echo "localhost 10015 cli" >> hosts.txt
echo "localhost 10016 cli" >> hosts.txt
echo "localhost 10017 cli" >> hosts.txt
echo "localhost 10018 cli" >> hosts.txt

#############################################################

# Launch all consensus drivers (must match hosts.txt)
# Argument format is [UID] [IS_LAST_NODE]
# UIDs must be from 0 to n-1

python3 condriver.py 0 &
python3 condriver.py 1 &
python3 condriver.py 2 &
python3 condriver.py 3 &
python3 condriver.py 4 &
python3 condriver.py 5 &
python3 condriver.py 6 &
python3 condriver.py 7 &
python3 condriver.py 8 &
python3 condriver.py 9 &
python3 condriver.py 10 &

# Launch all client drivers
# Note that proposers cannot be determined here since they are decided amongst the processes themselves during runtime
# Argument format is [UID] [V] [P] where V is the value the client wants to assign the global variable
#                       P is the desired proposer index, which is calculated modulo the length of proposers

python3 clidriver.py 11 55 0 &
python3 clidriver.py 12 56 1 &
python3 clidriver.py 13 57 2 &
python3 clidriver.py 14 57 3 &
python3 clidriver.py 15 230 1 &
python3 clidriver.py 16 231 45 &
python3 clidriver.py 17 232 41 &
python3 clidriver.py 18 233 10 &