#!/bin/bash

pkill -f python

# Update hosts.txt (must match consensus drivers list below this section)
echo "PROPOSERS 2" > hosts.txt
echo "ACCEPTORS 3" >> hosts.txt
echo "LEARNERS 44" >> hosts.txt
echo "localhost 10000 con" >> hosts.txt
echo "localhost 10001 con" >> hosts.txt
echo "localhost 10002 con" >> hosts.txt
echo "localhost 10003 con" >> hosts.txt
echo "localhost 10004 cli" >> hosts.txt

# Launch all consensus drivers (must match hosts.txt)
# Argument format is [UID] [IS_LAST_NODE]
# UIDs must be from 0 to n-1

python3 condriver.py 0 false &
python3 condriver.py 1 false &
python3 condriver.py 2 false &
python3 condriver.py 3 true &

# Ensure the last condriver has "true" set for its final flag 
# and that it is run after all the others

# Launch all client drivers
# Note that proposers cannot be determined here since they are decided amongst the processes themselves during runtime
# Argument format is [V] where V is the value the client wants to assign the global variable

python3 clidriver.py 4 55