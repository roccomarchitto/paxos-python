#!/bin/bash

# TODO silence error messages
pkill -f python

# Update hosts.txt (must match consensus drivers list below this section)
echo "PROPOSERS 3" > hosts.txt
echo "ACCEPTORS 5" >> hosts.txt
echo "LEARNERS 3" >> hosts.txt # Recall last con is always a learner, so learners must be >= 1
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

#############################################################

# Launch all consensus drivers (must match hosts.txt)
# Argument format is [UID] [IS_LAST_NODE]
# UIDs must be from 0 to n-1

python3 condriver.py 0 false &
python3 condriver.py 1 false &
python3 condriver.py 2 false &
python3 condriver.py 3 false &
python3 condriver.py 4 false &
python3 condriver.py 5 false &
python3 condriver.py 6 false &
python3 condriver.py 7 false &
python3 condriver.py 8 false &
python3 condriver.py 9 false &
python3 condriver.py 10 true &

# Ensure the last condriver has "true" set for its final flag 
# and that it is run after all the others

# Launch all client drivers
# Note that proposers cannot be determined here since they are decided amongst the processes themselves during runtime
# Argument format is [UID] [V] where V is the value the client wants to assign the global variable

python3 clidriver.py 11 55 &
python3 clidriver.py 12 56 &
python3 clidriver.py 13 57 &
python3 clidriver.py 14 57 &
python3 clidriver.py 15 230 &