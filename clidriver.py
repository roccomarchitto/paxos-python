#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The client driver for Paxos. Sends a value to a proposer node.

Usage: "python3 clidriver.py [v]" where v is the value the client wants to propose as the global variable.
"""
from paxos.client import ClientNode
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("uid", help="the unique identifier of the client node")
parser.add_argument("v", help="value the user wants to assign the global variable")
parser.add_argument("proposer", help="the proposer the user wants to assign the global variable to")
args = parser.parse_args()
VAL = args.v
UID = int(args.uid)
PROPOSER = int(args.uid)

# Read in the hosts.txt file
PROPOSERS = -1
ACCEPTORS = -1
LEARNERS = -1
HOSTS = []
with open("./hosts.txt","r") as f:
    PROPOSERS = int(f.readline().strip("\n").split(" ")[1])
    ACCEPTORS = int(f.readline().strip("\n").split(" ")[1])
    LEARNERS = int(f.readline().strip("\n").split(" ")[1])
    while (line := f.readline().rstrip()):
        line = line.strip("\n").split(" ")
        HOSTS.append([line[0],line[1],line[2]])


if __name__ == "__main__":
    node = ClientNode((PROPOSERS,ACCEPTORS,LEARNERS),HOSTS,UID,VAL,PROPOSER)
    node.InitializeNode() # Wait to receive list of proposers
    # Now with the list of proposers, we can choose one and send a proposal
    node.Set(VAL) # Attempt to set the global variable to VAL
    node.CleanupNode()