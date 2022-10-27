#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implements the ConsensusNode class (proposer, acceptor, and learner roles in Paxos)
"""
from __future__ import annotations
import abc
import math
from socket import *
from threading import Thread, Lock
import os
import sys
import pickle
import time
import random

BUFFER_SIZE = 4096

PROPOSERS = -1
ACCEPTORS = -1
LEARNERS = -1

DEBUG = False

BACKOFF = False

queue_lock = Lock() # Global mutex lock for the listener queue

class IConsensusNode(abc.ABC):
    """
    Core Paxos consensus methods
    """
    @abc.abstractmethod
    def __init__(self, mode_counts: List[int], hosts: List[List[str]], uid: int) -> None:
        """
        Called exactly once for a process, at process start.

        Parameters:
            mode_counts (tuple[int]): tuple (proposers,acceptors,learners) of the counts for the 3 different modes
            hosts (List[Lint[int]]): List of lists [hostname, port, consensus or client] for the hosts
            uid (int): Unique identifier for this host
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    def InitializeNode(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def Run(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def CleanupNode(self) -> None:
        raise NotImplementedError


class ConsensusNode(IConsensusNode):
    """
    Implementation of the IConsensusNode interface.
    Contains core Paxos methods as well as network interface methods.
    """
    def __init__(self, mode_counts: tuple[int], hosts: List[List[str]], uid: int) -> None:
        global PROPOSERS, ACCEPTORS, LEARNERS
        PROPOSERS = mode_counts[0]
        ACCEPTORS = mode_counts[1]
        LEARNERS = mode_counts[2]
        self.hosts = hosts  # hosts format: [[hostname,port,cli or con],...] where the list is indexed by uid
        self.host_info = hosts[uid] # host_info is a list [hostname, port, consensus or client]
        self.uid = uid
        self.port = int(self.host_info[1])
        self.hostname = self.host_info[0]
        self.type = self.host_info[2] # either con for consensus node or cli for client node
        self.role = "" # To be populated; either PROPOSER, ACCEPTOR, or LEARNER
        
        self.message_queue = [] # Network messages go here

        # List of consensus nodes
        self.con_nodes = list(filter(lambda x: x[2] == "con", self.hosts))
        # List of client nodes
        self.cli_nodes = list(filter(lambda x: x[2] == "cli", self.hosts))

        """
        Determine the leader for role election (i.e., the highest UID)
        """
        # Naive approach, just select max in con_nodes (this works, but doesn't preclude failing nodes)
        #if self.uid == len(self.con_nodes)-1:
        #    self.is_leader = True
        
        # Leader election approach - embed a ring topology and complete Chang-Roberts
        self.is_leader = False
        self.leader_is_chosen = False
        self.ChangRoberts()
        
        while not self.leader_is_chosen:
            continue
        if DEBUG: print(f"LEADER CONSENSUS: {self.uid},{self.is_leader}")
        
        # List of each role, gets populated later
        self.proposers = []
        self.acceptors = []
        self.learners = []

        # The unique sequence number; increments by len(hosts) each time it is needed to increment
        # This forces disjoint sequence number sets
        self.seq = self.uid

        self.acceptances = [] # Acceptances received
        self.proposals = [] # Proposals made
        self.promises = [] # Promises received
        self.acks = [] # Acks received



    """
    Leader election via Chang-Roberts
    """

    def ChangRoberts(self) -> None:
        """
        Select a leader based on UIDs using an embedded ring topology.
        Chang-Roberts is O(n^2) message complexity.
        Pseudocode:
        First each process is red and sends a token to its neighbor with its UID.
        Receive tokens:
            If red:
                If a lower token is received, ignore and that token gets removed so it quits.
                If a higher token is received, set color to black and forward the token
                If the same ID token is received, set self to leader, terminate algorithm
            If black:
                Forward all tokens
        """
        # First send a token to the neighbor
        neighbor_id = (self.uid+1) % len(self.con_nodes)
        rec_port = self.hosts[neighbor_id][1] # Neighbor's port
        self.color = "RED";

        # Start the Chang-Roberts listener thread
        self.crlistener = Thread(target=self.ChangRobertsListener, name=f"crlistener{self.uid}:{self.port}")
        self.crlistener.start()

        # After a brief wait, forward initial token
        time.sleep(0.1)
        self.udp_send("TOKEN",self.uid,"localhost",rec_port)

    def ChangRobertsListener(self) -> None:
         with socket(AF_INET, SOCK_DGRAM) as udp_socket:
            try:
                udp_socket.bind(("", self.port))
                while True:
                    """
                    Pseudocode for listener thread:
                    Receive tokens:
                        If red:
                            If a lower token is received, ignore and that token gets removed so it quits.
                            If a higher token is received, set color to black and forward the token
                            If the same ID token is received, set self to leader, terminate algorithm
                        If black:
                            Forward all tokens
                    """
                    # Receive and deserialize messages
                    # Message is a dictionary with keys HEADER, MESSAGE, RECIPIENT, and PORT
                    message, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                    message = pickle.loads(message)
                    
                    neighbor_id = (self.uid+1) % len(self.con_nodes)
                    rec_port = self.hosts[neighbor_id][1] # Neighbor's port

                    # Check if a token was received
                    if message["HEADER"] != "TOKEN":
                        raise Exception("Non-token sent in Chang-Roberts!",message)
                    
                    if message["MESSAGE"] != "TERM": # If not a termination message, follow Chang-Roberts
                        token = int(message["MESSAGE"])
                        if self.color == "BLACK": # Always forward
                            self.udp_send("TOKEN",self.uid,"localhost",rec_port)
                        else: # Color is red, so compare token
                            i = self.uid
                            j = token
                            if (j < i):
                                pass # skip, do nothing
                            if (j > i):
                                # send j, set color to black
                                self.color = "BLACK"
                                self.udp_send("TOKEN",j,"localhost",rec_port)
                            if (j == i):
                                time.sleep(0.1)
                                self.is_leader = True
                                self.leader_is_chosen = True
                                self.udp_multicast("TOKEN","TERM",self.con_nodes)
                                print(f"\n=================================\nNode ID {i} IS THE LEADER")
                    else: # Message is terminate, so exit ChangRoberts
                        self.leader_is_chosen = True
                        return

            finally:
                udp_socket.close()

    def InitializeNode(self) -> None:
        global PROPOSERS, ACCEPTORS, LEARNERS
        
        # Detect if n-1st (final) con node
        if self.is_leader:
            # If this is true, this node is the "consensus master"
            # It is responsible for delegating proposer/acceptor/learner roles
            
            time.sleep(0.05) # Wait for other nodes to initialize
            
            idx = 0
            # Recall self.hosts[idx][0] is the hostname of the idxth host, 1 is the port
            for i in range(PROPOSERS):
                self.udp_send("ROLE","PROPOSER",self.hosts[idx][0],self.hosts[idx][1])
                self.proposers.append(idx)
                idx += 1
            for i in range(ACCEPTORS):
                self.udp_send("ROLE","ACCEPTOR",self.hosts[idx][0],self.hosts[idx][1])
                self.acceptors.append(idx)
                idx += 1
            for i in range(LEARNERS):
                self.udp_send("ROLE","LEARNER",self.hosts[idx][0],self.hosts[idx][1])
                self.learners.append(idx)
                idx += 1
            # By this setup, the n-1st node is always a learner (message above gets lost, but that is OK and the idx append is still needed)
            self.role = "LEARNER"

            # After a brief wait to get everyone else situated, we allow the initialization to end
            time.sleep(0.1) 
            if DEBUG: print("NOTIFYING CLIENT NODE TO BEGIN PROPOSALS")
            
        else: # If not the last node, then wait to learn role
            with socket(AF_INET, SOCK_DGRAM) as udp_socket:
                try:
                    udp_socket.bind(("", self.port))
                    while True:
                        # Receive and deserialize messages
                        # Message is a dictionary with keys HEADER, MESSAGE, RECIPIENT, and PORT
                        message, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                        message = pickle.loads(message)
                        if message["HEADER"] != "ROLE": # Might be a leftover message from leader election
                            continue
                        else:
                            self.role = message["MESSAGE"]
                            return
                finally:
                    udp_socket.close()
            

    def Run(self) -> None:
        # First set up a listener thread for incoming messages
        print(f"Node ID {self.uid} is running as a {self.role}")

        # For all hosts, set up a FIFO queue for incoming connections
        self.queue_listener = Thread(target=self.queue_listen, name=f"queue_listener{self.uid}:{self.port}")
        self.queue_listener.start()

        # For all hosts, set up a listener thread
        self.listener = Thread(target=self.udp_listen, name=f"listener{self.uid}:{self.port}")
        self.listener.start()

        # The leader should notify the clients and consensus nodes of the role assignments (after a brief delay)
        if (self.is_leader):
            self.udp_multicast("START",(self.proposers,self.acceptors,self.learners),self.hosts)
        

    def CleanupNode(self) -> None:
        # No need to implement this for basic Paxos; may be implemented in the future
        pass


    def queue_listen(self) -> None:
        """
        Listen for and handle updates to the request queue.

        This function handles the majority of the Paxos logic.
        """
        while True:
            if len(self.message_queue) > 0:
                # First receive any messages in the queue that need to be handled
                queue_lock.acquire()
                try:
                    message = self.message_queue.pop(0)
                finally: 
                    queue_lock.release()

                # The leader sends all role assignments in a START message
                # Each node keeps a local copy of this
                # After receipt of this message, other messages may be completed
                if message["HEADER"] == "START":
                    roles_tuple = message["MESSAGE"]
                    self.proposers = [self.hosts[i] for i in roles_tuple[0]]
                    self.acceptors = [self.hosts[i] for i in roles_tuple[1]]
                    self.learners = [self.hosts[i] for i in roles_tuple[2]]


                # Check if a terminate message is sent
                if message["HEADER"] == "TERM":
                    os._exit(0) # Exit program and all threads


                # Check if a message is being forwarded from a client
                # This will initiate Paxos phase 1.1
                if message["HEADER"] == "FWD":
                    if self.role != "PROPOSER":
                        raise Exception(f"Message sent to incorrect recipient: {message}")
                    """
                    Pseudocode: Send the proposal (v,n) to each acceptor.
                    """
                    VAL = message["MESSAGE"]
                    if DEBUG: print(f"Forwarded value received by {self.role} (ID {self.uid}): {VAL}. Beginning Phase 1.1 at seq {self.seq}...\n")
                    msg = (VAL,self.seq)
                    self.udp_multicast("PROPOSAL",msg,self.acceptors)
                    # Increase the sequence number for future messages
                    # Increasing by len(hosts) keeps sequence numbers disjoint
                    self.seq += len(self.hosts)
                    
                

                if message["HEADER"] == "PROPOSAL":
                    if self.role != "ACCEPTOR":
                        raise Exception(f"Message sent to incorrect recipient: {message}")
                    """
                    The receipt of this message initiates Paxos phase 1.2
                    A message (v,n) w/ message v and sequence number n is received.
                    Pseudocode:
                    Store all sent promises in a promise list.
                    If n is the largest proposal received, send a promise: ack(n,_,_)
                        and ignore proposals labeled less than n
                    If an ACCEPTOR has ACCEPTED a proposal w/ number n' < n, send a promise: ack(n,v1,n')
                        this tells the proposer to send ACCEPT messages w/ value v1 rather than v
                        (alternatively, a nack can be sent)
                    """

                    """
                    #######################
                    # TODO: ADD FAILURE TESTS HERE
                    # Change these UIDs to any value
                    if self.uid == 5 or self.uid == 6: 
                        os._exit(0)
                    #######################
                    """

                    # Decode the proposal as a tuple (v,n)
                    (v,n) = message["MESSAGE"]
                    if DEBUG: print(f"An {self.role} (ID {self.uid}) received {v} @ seq {n}")
                    
                    # Check if n is the largest sequence number received
                    # The list copy is done for safety purposes
                    temp = self.promises.copy()
                    temp.append((v,n))
                    greater_proposals = list(filter(lambda x: x[1] > n, temp))
                    
                    if len(greater_proposals) == 0: # There is no greater proposal, so make a promise
                        # Two cases:
                        # (1) No accepted value has been seen yet -> send ack(n,v,_)
                        # (2) An accepted value at n1 < n has been seen -> send ack(n,v,n1)
                        rec_port = self.hosts[message["SENDERID"]][1]
                        if self.acceptances:
                            # If there are accepted values, need to find the highest sequence number
                            # and send the value associated with it
                            max_tuple = self.acceptances[0]
                            for t in self.acceptances:
                                if t[1] > max_tuple[1]:
                                    max_tuple = t
                            ack = (n,max_tuple[0],max_tuple[1]) # Discard old values, replace w/ already accepted values
                            self.promises.append((max_tuple[0],max_tuple[1]))
                            # Note that (max_tuple[0],max_tuple[1]) corresponds to (vx,nx) of the highest nx accepted
                            if DEBUG: print("SENDING (n,v,n') ACK")
                            self.udp_send("ACK",ack,"localhost",rec_port)
                        else:    
                            # No accepted values, so just ack the n and v we were sent
                            ack = (n,v,"_")
                            self.promises.append((v,n))
                            if DEBUG: print("SENDING (n,v,_) ACK")
                            self.udp_send("ACK",ack,"localhost",rec_port)
                    else: # There was a greater proposal - send a NACK
                        if DEBUG: self.udp_send("NACK",(v,n),"localhost",rec_port)
                

                if message["HEADER"] == "NACK":
                    if self.role != "PROPOSER":
                        raise Exception(f"Message sent to incorrect recipient: {message}")
                    # Backoff can be unpredictably very inefficienct; it is not recommended
                    # The use of NACKs generally avoids race conditions so backoff is not required
                    if BACKOFF:
                        (v,n) = message["MESSAGE"]
                        # Send a message to self to "reforward" from client (retry)
                        time.sleep(random.choice([0.05*x for x in range(20)])) # Wait a small random amount of time
                        self.udp_send("FWD",v,"localhost",self.port) # self on self.port since we are sending to self


                if message["HEADER"] == "ACK":
                    if self.role != "PROPOSER":
                        raise Exception(f"Message sent to incorrect recipient: {message}")
                    """
                    The recipient of this message initiates (or continues) Paxos phase 2.1
                    An ack(n,v,n') is received from an acceptor and this determines the contents of the proposer's ACCEPT message.
                    Pseudocode:
                    Store ack(_,_,_) in an ack list.
                    Check if attached timestamp n forms a majority. If majority:
                        Send ACCEPT(v,n) where v is the value of the highest n ack received

                        If ack(n,v,_) is received then send ACCEPT(v,n)
                        If ack(n,v',n') is received at any time (meaning a value was accepted already)
                            override v to use v', and send ACCEPT(v',N), where N is the HIGHEST sequence number seen
                    """
                    (n1,v,n2) = message["MESSAGE"]
                    if DEBUG: print(f"Ack received at {self.role} {self.uid}: {(n1,v,n2)} with acceptances list {self.acceptances}")
                    # Important note: If acceptances not counted in phase 1 are found here, they still need to be accounted for
                    # This can be done with "ghost" messages
                    
                    min_majority = math.floor(len(self.acceptors)/2) + 1 # The minimum number of acceptors that constitutes a majority
                    
                    self.acks.append((n1,v,n2))

                    # Check if majority has been received for n1 being sent in
                    n1_ack_list = list(filter(lambda x: (x[0]==n1 or x[2]==n1), self.acks))
                    
                    if len(n1_ack_list) >= min_majority:
                        if DEBUG: print("MAJORITY ACHIEVED BY PROPOSER - SENDING ACCEPT REQUEST TO ALL ACCEPTORS")
                        # The accept message is (v,n)
                        # Here v is the value of the highest-numbered proposal
                        # n is n1

                        # Find highest n ack received
                        # Note that ack[2] is always less than or equal to ack[0], so only check ack[0]
                        highest_ack = self.acks[0]
                        for ack in self.acks:
                            if ack[0] > highest_ack[0]:
                                highest_ack = ack

                        # If there are accepted values, need to find the highest sequence number (ghost messages)
                        # and send the value associated with it
                        max_tuple = tuple()
                        if self.acceptances:
                            
                            max_tuple = self.acceptances[0]
                            for t in self.acceptances:
                                if t[1] > max_tuple[1]:
                                    max_tuple = t # (v,n) that must be sent
                            accept_req = max_tuple
                            if DEBUG: print("PROPOSAL OVERRULED BY ALREADY ACCEPTED MESSAGE",accept_req)
                            self.udp_multicast("ACCEPT",accept_req,self.acceptors)
                        else:
                            accept_req = (highest_ack[1],n1)
                            self.udp_multicast("ACCEPT",accept_req,self.acceptors)
                    
                    
                
                if message["HEADER"] == "ACCEPT":
                    if self.role != "ACCEPTOR":
                        raise Exception(f"Message sent to incorrect recipient: {message}")
                    """
                    The recipient of this message initiates Paxos phase 2.2
                    An ACCEPT(v,n) is accepted unless there is a promise to a sequence number greater than n.
                    Pseudocode:
                    If ack(n,_,_) or ack(_,_,n) found in promise list, ignore.
                    Else accept v and n, and add to the accept list.
                    Forward values to learner
                    """

                    # Reminder - proposals and accept requests are (v,n), acks are (n1,v,n2) format
                    if DEBUG: print(f"Accept request received by a {self.role} (ID {self.uid}): {message}")
                    (v,n) = message["MESSAGE"]
                    # Check if a promise has (v1,n1), where n1 < n (don't accept in this case)
                    greater_promises = list(filter(lambda x: x[1] > n, self.promises))
                    if len(greater_promises) == 0:
                        # Send to the learner since no greater promises were made
                        self.udp_multicast("ACCEPT-VALUE",(v,n),self.proposers)
                        self.udp_multicast("LEARN",(v,n),self.learners) 
                        if DEBUG: print(f"{(v,n)} HAS BEEN ACCEPTED",self.learners)
                    else:
                        if DEBUG: print(f"Accept request rejected {self.role} (ID {self.uid}): {message}")


                if message["HEADER"] == "LEARN":
                    if self.role != "LEARNER":
                        raise Exception(f"Message sent to incorrect recipient: {message}")
                    """
                    The recipient of this message initiates (or continues) Paxos phase 3.
                    It collects accepted values and decides on a majority.
                    Pseudocode:
                    On receipt of (v,n), add the accepted value to a list of accepted values
                    If the list reaches a majority, multicast to clients
                    """
                    if DEBUG: print(f"Accepted value received: {message['MESSAGE']}")
                    (v,n) = message["MESSAGE"]
                    self.acceptances.append((v,n))
                    min_majority = math.floor(len(self.acceptors)/2) + 1 # The minimum number of acceptors that constitutes a majority
                    # Check if majority has been received for n1
                    acceptance_list = list(filter(lambda x: (x[1]==n), self.acceptances))
                    if DEBUG: print("Acceptances and minimum majority:",len(acceptance_list),min_majority)
                    if len(acceptance_list) >= min_majority:
                        if DEBUG: print("MAJORITY ACHIEVED BY ACCEPTORS.")
                        self.udp_multicast("SET",v,self.cli_nodes)
                    

    """
    Network interface methods
    """
    def udp_multicast(self, header: str, message: str, group: List[List[str]]) -> None:
        # group is a list of hosts (lists) [[hostname,port,type],...]
        for rec in group:
            self.udp_send(header, message, rec[0], int(rec[1]))


    def udp_send(self, header: str, message, recipient: str, port: int) -> None:
        """
        All outgoing messages are sent through this handler.

        Parameters:
            header (str): The header that defines the message type
            message (str): The raw string message to send
            recipient (str): The hostname of the recipient
            port (int): The port of the recipient 
        """
        # Define and serialize the message to byte form before sending
        message =   {
                        'HEADER': header,
                        'MESSAGE': message,
                        'RECIPIENT': recipient,
                        'PORT': int(port),
                        'SENDERID': int(self.uid)
                    }
        message = pickle.dumps(message)
        
        # Send the message over UDP
        with socket(AF_INET, SOCK_DGRAM) as udp_socket:
            udp_socket.sendto(message, (recipient, int(port)))
    

    def udp_listen(self) -> None:
        """
        Listen for incoming UDP messages, deserialize, and handle.
        """
        with socket(AF_INET, SOCK_DGRAM) as udp_socket:
            try:
                udp_socket.bind(("", self.port))
                while True:
                    # Receive and deserialize messages
                    # Message is a dictionary with keys HEADER, MESSAGE, RECIPIENT, and PORT
                    message, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                    message = pickle.loads(message)

                    # If a proposer is receiving accept messages, bypass queue
                    if message["HEADER"] == "ACCEPT-VALUE":
                        if DEBUG: print(f"Proposer received notice of accepted value: (ID {self.uid}) received {message}")
                        (v,n) = message["MESSAGE"]
                        self.acceptances.append((v,n))
                        # Forward to learner (this is added redundancy due to possible network/concurrency failure, see documentation)
                        self.udp_multicast("LEARN",(v,n),self.learners)

                    else: # Else add to the message queue
                        queue_lock.acquire()
                        try:
                            self.message_queue.append(message)
                        finally: 
                            queue_lock.release()
            finally:
                udp_socket.close()