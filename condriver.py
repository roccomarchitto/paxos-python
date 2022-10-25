#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Driver for consensus nodes.

Usage: "python3 condriver.py [UID] [IS_LAST_NODE]", where UID is a unique ID and IS_LAST_NODE
"""
from paxos.consensus import ConsensusNode
import argparse

# Parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument("uid", help="unique identifier")
parser.add_argument("is_last_node", help="is this the last (n-1th) consensus node?")
args = parser.parse_args()
UID = int(args.uid)
IS_LAST_NODE = args.is_last_node

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
    #print("Can start algorithm now for",UID)
    node.Run()

