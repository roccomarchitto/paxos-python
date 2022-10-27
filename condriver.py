#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Driver for consensus nodes.

Usage: "python3 condriver.py [UID]", where UID is a unique ID
"""
from paxos.consensus import ConsensusNode
import argparse

# Parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument("uid", help="unique identifier")
args = parser.parse_args()
UID = int(args.uid)

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
    node = ConsensusNode((PROPOSERS,ACCEPTORS,LEARNERS),HOSTS,UID)
    node.InitializeNode()
    node.Run()
    # Note that node exit is handled through clients, so there is no need for calling cleanup here

