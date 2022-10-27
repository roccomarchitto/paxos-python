# Basic Paxos in Python
This is a Python library implementing the basic Paxos algorithm. It also implements the Chang-Roberts leader election algorithm.

## Testing
### The shell file
The shell files are the main entry point to testing the program. There are a few example shell files - run.sh, run2.sh, and run3.sh. Run these by navigating to the root folder and typing, for example, `./run.sh`. The output should print the selected leader, the proposer/acceptor/learner assignments, and "Final message received by client from learner" messages which indicate the final consensus.

The run shell files have a few components (I apologize for the complexity). The line `pkill -f python 2>/dev/null` is needed to avoid Python ports getting clogged up on consecutive runs. This command also hides errors which appear on Isengard due to security issues.

There are two components in a run file which must match: the section that updates hosts.txt with ports and node types, and the section that launches the drivers. These must have the same number of nodes. Please pay careful attention to this section as it is easy to misformat.

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
[ID] is the unique ID, which must be in n, n+1, ..., m+n-2. [VALUE] is the value that the client wants to set the global variable to. [DESIREDPROPOSER] is the desired ID of the proposer - note that the chosen proposer is computed modulo the length of the proposers list (calculated during runtime), so there is no need for exact proposer IDs. Example: For 2 proposers, `DESIREDPROPOSER=0` selects the first proposer, `1` selects the second proposer, and `2` selects the first one since modulo is done.

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

For more detailed console traces, flip the `DEBUG` global variable in `consensus.py`. Note that these messages are not necessarily in correct order.


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

The leader then broadcasts to the consensus nodes that a leader has been chosen, and the non-leader consensus nodes wait to be assigned their roles. The leader then assigns their roles (proposer, acceptor, or learner), and broadcasts a `START` message to *all* nodes, which informs the clients they can message the proposers. In the initialization period, each consensus node also sets up a listener thread and a listening queue. The listening thread pushes to the queue.

Sequence numbers are handled as follows: every node's initial sequence number is its ID. Every time it makes a proposal, it increases its sequence number by the length of the number of hosts. This creates a monotonically increasing disjoint sequence of numbers for each consensus node, as Paxos requires.

The queue processes the message headers; the ones specific to Paxos are `FWD` which initiates phase 1.1, `PROPOSAL` which runs phase 1.2, `ACK`, which runs 2.1, `ACCEPT`, which runs 2.2, and `LEARN`, which runs phase 3 and is the last step where learner nodes receive accepted values and check for a majority. The algorithm is implemented exactly as described in the Ghosh textbook. Please see the comments in `consensus.py` for pseudocode and specific details.

`NACK` messages are sent to discourage proposers from trying again by raising their sequence numbers. Note that if the global variable `BACKOFF` is set to true, then after a short random wait, the node will try again. This is not needed as race conditions are highly unlikely with the implementation style. It is not recommended to use this setting as it stalls performance significantly.

All messages are sent using UDP. Note that there are some small `time.sleep(n)` lines throughout which are for safety and concurrency purposes (this is not the best practice, but it suffices for this project). To avoid these I would implement an ack system and probably opt for TCP rather than UDP.

## Assumptions and Other Notes

- No failures in the initialization; we assume the initialization is fully complete before any proposals are sent. We also assume there are no concurrency issues or incorrect message sequences.
- The program is tested with up to 11 consensus nodes of various permutations, and 4 client nodes submitting to different proposers. It is unknown how well the program scales so we assume a low number of consensus nodes until further testing.
- Note that there is a significant amount of redundancy in this model. This is why the "Final message received" by clients is printed more times than there are clients. This is expected.
- Each consensus node is exactly 1 role.
- There is always at least one learner; the n-1st consensus-node will always be given the role learner (the n-1st node gets designated the leader by Chang-Roberts).
- Machines are all on the same network (hostname is always "localhost").
- Consensus node IDs are always lower numbered than client node IDs.
- No proposer nodes fail.
- The majority of acceptor nodes do not fail; for 2m+1 acceptor nodes, this implementation can handle a maximum of m acceptor nodes failing.
- It is highly discouraged to flip the `BACKOFF` global variable to true; race conditions are avoided with `NACK` messages so this is not needed and only introduces redundant message sending and possible termination delay. Regardless, the `BACKOFF` functionality does exist in the program.
- In rare occurrences, due to network or concurrency failures, messages may be mismatched causing Byzantine failures. An exception will be thrown whenever possible, and in this case just restart the program.
- If a client does not print its value, it may be due to one of the failures mentioned above. This does not always mean consensus has not been reached among the acceptors (the debug logs can prove this). Again, in this case, just restart the program. Note that these occurrences are rare.