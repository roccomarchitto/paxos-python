# Basic Paxos in Python
This is a Python library implementing the basic Paxos algorithm.

### Important Note
 If a client does not print out its received value, it does not necessarily mean the algorithm broke. There is a recurring bug where the client doesn't get the message (possibly from network, concurrency, or I/O failures), but the consensus value is in fact set (the debug logs can prove this). If this happens, just run the script again.

## Testing
### The shell file
The shell files are the main entry point to testing the program. There are a few example shell files - run.sh, run2.sh, and run3.sh. Run these by navigating to the folder and typing, for example, `./run.sh`.

The run shell files have a few components. The line `pkill -f python 2>/dev/null` is needed to avoid Python ports getting clogged up on consecutive runs. This command also hides errors which appear on Isengard due to security issues.

There are two components in a run file which must match: the section that updates hosts.txt with ports and node types, and the section that launches the drivers. Please pay careful attention to this section as it is easy to misformat.

Suppose there are `n` consensus nodes. The first 3 lines of the update to hosts.txt section should be as follows for x, y, z desired proposers, acceptors, and learners, respectively, where x+y+z=n:
```
echo "PROPOSERS x" > hosts.txt
echo "ACCEPTORS y" >> hosts.txt
echo "LEARNERS z" >> hosts.txt
```
Then, for each consensus node, add a line such as:
```
echo "localhost [PORT] con" >> hosts.txt
```
where [PORT] is the port number and con stands for consensus. For each client node, add a line such as:
```
echo "localhost 10005 cli" >> hosts.txt
```
Now we must launch the consensus drivers, exactly one for each node above. Note that these strictly must have their IDs be 0 to n-1. A consensus node is launched as follows:
```
python3 condriver.py [ID] &
```
A client driver is launched as follows:
```
python3 clidriver.py [ID] [VALUE] [DESIREDPROPOSER] &
```
[ID] is the unique ID, which must be in n, n+1, ..., m+n-2. [VALUE] is the value that the client wants to set the global variable to. [DESIREDPROPOSER] is the desired ID of the proposer - note that this value is computed modulo the length of the proposers list (calculated during runtime), so there is no need for exact proposer IDs. A 0 for this value is the 1st proposer, and a 1 is the second, assuming there are at least 2 proposers.

An example run.sh (using the simplest Paxos setup) is as follows:
```
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
```
### Failure testing
IMPORTANT: On any run, a majority of the acceptor nodes must not fail. This is required to reach acceptance. If this condition does not hold, majority acceptance might still occur, but the learners will never learn about it.

To test failure of nodes, a good spot to do this is in the handler for Paxos phase 1.2. This section begins with the if statement `if message["HEADER"] == "PROPOSAL"`.  This should be around line 350 in `consensus.py`. Uncomment the code
```
if self.uid == 3 or self.uid == 4 or self.uid == 1:
    exit(0)
```
and change the UID values to your preference.


## Design
### The driver files
There are two driver files, `clidriver.py` and `condriver.py` in the root directory. These both parse input, read hosts.txt, and launch a single node using the library functions, for example:
```
node = ClientNode((PROPOSERS,ACCEPTORS,LEARNERS),HOSTS,UID,VAL,PROPOSER)
    node.InitializeNode() # Wait to receive list of proposers
    # Now with the list of proposers, we can choose one and send a proposal
    node.Set(VAL) # Attempt to set the global variable to VAL
    node.CleanupNode()
```
Note that consensus nodes do not have a cleanup function as they are shut down from client-originating messages.

### client.py
The `client.py` file in the `paxos` folder implements the `ClientNode` class. Briefly, its flow is as follows: first, the hosts and command line arguments are sent for initialization. Then when `InitializeNode()` is called, the client blocks until it receives a message from the consensus node leader containing the list of proposers. It then selects a proposer based on the command line argument passed in for this, and is now ready to run. 

On `Set(value)`, the client waits a short period of time as a safety check for the other nodes to be ready, and then proposes `value` to its designated proposer consensus node, and then waits for a value to arrive. The value that arrives is the consensus value. 

After this, the learner will `break` from its listener while loop (note that this behavior can be changed to see all accepted values, just remove the break statement in the function `wait()`) and unblock. Then on `CleanupNode()`, the client waits 5 seconds and then sends a terminate signal to every node in the distributed system.

### consensus.py

The `consensus.py` file implements the `ConsensusNode` class. It has some complex logic in it, so this documentation will only cover its design at a high level. On initialization, the line `self.ChangRoberts()` is run which uses the Chang-Roberts leader election algorithm (as described on page 230, Chapter 11 in Ghosh) to select a leader. This is done by embedding a ring topology using modular arithmetic on the UIDs.

The leader then broadcasts to the consensus nodes that a leader has been chosen, and the non-leader consensus nodes wait to be assigned their roles. The leader then assigns their roles (proposer, acceptor, or learner), and broadcasts a `START` message to *all* nodes, which informs the clients they can message the proposers. In the initialization period, each consensus node also sets up a 

After the proposers 

Note that there are some small `time.sleep(n)` lines throughout which are for safety and concurrency purposes (this is not the best practice, but it suffices for this project).



## Assumptions

- No failures in the initialization; we assume the initialization is fully complete before any proposals are sent
- Each consensus node is exactly 1 role
- There is always at least one learner; the n-1st consensus-node will always be given the role learner (the n-1st node gets designated the leader by Chang-Roberts)
- Machines are all on the same network (hostname is always "localhost")
- In IDs, consensus-nodes always come before client-nodes
- No proposer nodes fail
- The majority of acceptor nodes do not fail

- Possible bug w/ backoff taking a long time. Also, sometimes messages get mismatched for an unknown reason. These are rare occurrences.

