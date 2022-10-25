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
import pickle
import time
import random

BUFFER_SIZE = 4096

PROPOSERS = -1
ACCEPTORS = -1
LEARNERS = -1

DEBUG = True

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
        """

        """
        raise NotImplementedError

    @abc.abstractmethod
    def Run(self) -> None:
        """

        """
        raise NotImplementedError

    @abc.abstractmethod
    def CleanupNode(self) -> None:
        """

        """
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
        self.is_leader = False
        self.message_queue = [] # Network messages go here

        # Detect if leader w/ list of consensus nodes
        self.con_nodes = list(filter(lambda x: x[2] == "con", self.hosts))
        if self.uid == len(self.con_nodes)-1:
            self.is_leader = True
        #print(f'\nCONLIB CALLED for {uid}:\t{PROPOSERS},{ACCEPTORS},{LEARNERS},{self.host_info}')

        # List of client nodes
        self.cli_nodes = list(filter(lambda x: x[2] == "cli", self.hosts))

        # List of each role
        self.proposers = []
        self.acceptors = []
        self.learners = []

        # The unique sequence number; increments by len(hosts) each time it is needed to increment
        # This forces disjoint sequence number sets
        self.seq = self.uid

        self.acceptances = [] # Acceptors multicast acceptances to learners and proposers
        # Note that all roles are the same class, so role-specific variables and functions are all handled in the same class
        # Acceptor variables
        self.proposals = []
        self.promises = []
        self.acks = []



    def InitializeNode(self) -> None:
        global PROPOSERS, ACCEPTORS, LEARNERS

        # Detect if n-1st (final) con node
        #con_nodes = list(filter(lambda x: x[2] == "con", self.hosts))
        if self.is_leader:
            # If this is true, this node is the "consensus master"
            # It is responsible for delegating proposer/acceptor/learner roles
            
            time.sleep(0.05) # Wait for other nodes to initialize
            # TODO: Wait in a better way than sleeping
            
            print("CON MASTER",self.uid)
            idx = 0
            # Recall self.hosts[idx][0] is the hostname of the idxth host, 1 is the port
            for i in range(PROPOSERS):
                #print(f"Node {idx} is a PROPOSER")
                self.udp_send("ROLE","PROPOSER",self.hosts[idx][0],self.hosts[idx][1])
                self.proposers.append(idx)
                idx += 1
            for i in range(ACCEPTORS):
                #print(f"Node {idx} is an ACCEPTOR")
                self.udp_send("ROLE","ACCEPTOR",self.hosts[idx][0],self.hosts[idx][1])
                self.acceptors.append(idx)
                idx += 1
            for i in range(LEARNERS):
                #print(f"Node {idx} is a LEARNER")
                self.udp_send("ROLE","LEARNER",self.hosts[idx][0],self.hosts[idx][1])
                self.learners.append(idx)
                idx += 1
            # By this setup, the n-1st node is always a learner (message above gets lost, but that is OK and the idx append is still needed)
            self.role = "LEARNER"
            #print(f"Node {self.uid} has accepted role {self.role}")

            time.sleep(0.1)
            print("NOTIFYING CLIENT NODE TO BEGIN PROPOSALS")
            # After a brief wait to get everyone else situated, we allow the initialization to end
        else: # If not the last node, then wait to learn role
            with socket(AF_INET, SOCK_DGRAM) as udp_socket:
                try:
                    udp_socket.bind(("", self.port))
                    # Receive and deserialize messages
                    # Message is a dictionary with keys HEADER, MESSAGE, RECIPIENT, and PORT
                    message, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                    message = pickle.loads(message)
                    self.role = message["MESSAGE"]
                    #print(f"Node {self.uid} has accepted role {self.role}")
                    #print(f"Message received @ {self.uid}:",message)
                        
                finally:
                    udp_socket.close()
            

    def Run(self) -> None:
        # First set up a listener thread for incoming messages
        print(f"Running {self.uid} as a {self.role}")

        # For all hosts, set up a FIFO queue for incoming connections
        # TODO
        self.queue_listener = Thread(target=self.queue_listen, name=f"queue_listener{self.uid}:{self.port}")
        self.queue_listener.start()

        # For all hosts, set up a listener thread
        self.listener = Thread(target=self.udp_listen, name=f"listener{self.uid}:{self.port}")
        self.listener.start()

        # The leader should notify the clients and consensus nodes of the role assignments (after a brief delay)
        if (self.is_leader):
            self.udp_multicast("START",(self.proposers,self.acceptors,self.learners),self.hosts)
            #print(self.hosts)
        # TODO: Allow for choosing of a specific proposer
        
        

    def CleanupNode(self) -> None:
        pass

    

    def queue_listen(self) -> None:
        """
        Listen for and handle updates to the request queue.
        """
        while True:
            if len(self.message_queue) > 0:
                message = self.message_queue.pop(0)
                #print(message)

                # TODO mutex

                # Check if the leader is sending role assignments
                # TODO make sure this gets seen first
                if message["HEADER"] == "START":
                    roles_tuple = message["MESSAGE"]
                    self.proposers = [self.hosts[i] for i in roles_tuple[0]]
                    self.acceptors = [self.hosts[i] for i in roles_tuple[1]]
                    self.learners = [self.hosts[i] for i in roles_tuple[2]]


                # Check if a message is being forwarded from a client
                # This will initiate Paxos phase 1.1
                if message["HEADER"] == "FWD" and self.role == "PROPOSER":
                    VAL = message["MESSAGE"]
                    print(f"Forwarded value received: {VAL}. Beginning Phase 1.1...")
                    msg = (VAL,self.seq)
                    print(f"Sending {msg} to {self.acceptors}!")
                    self.udp_multicast("PROPOSAL",msg,self.acceptors)
                    # TODO sequence numbers
                    # TODO acceptor list
                

                if message["HEADER"] == "PROPOSAL":
                    if self.role != "ACCEPTOR":
                        raise Exception("Message sent to incorrect recipient")
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
                    
                    # First decode the proposal as a tuple (v,n)
                    (v,n) = message["MESSAGE"]
                    if DEBUG: print(f"An {self.role} (UID {self.uid}) received {v} @ sequence number {n}")
                    self.proposals.append((v,n)) # TODO check correctness of this logic
                    # Check if n is the largest sequence number received
                    greater_proposals = list(filter(lambda x: x[1] > n, self.proposals))
                    if len(greater_proposals) > 0:
                        # There is a greater sequence number we have made a promise to, so ignore this one
                        pass
                    else: # Make a promise
                        # We will send an ack, but need to first check if an ACCEPTOR has ACCEPTED A proposal w/ number n' < n
                        # TODO NOTE IMPORTANT
                        # use self.acceptances
                        ack = (n,v,"_")
                        self.promises.append((v,n))
                        # TODO udp_send to sender, not localhost
                        print("SENDING ACK")
                        self.udp_multicast("ACK",ack,self.proposers)
                                    


                if message["HEADER"] == "ACK":
                    if self.role != "PROPOSER":
                        raise Exception("Message sent to incorrect recipient")
                    """
                    The recipient of this message initiates (or continues) Paxos phase 2.1
                    An ack(a,b,c) is received from an acceptor and this determines the contents of the proposer's ACCEPT message.
                    Pseudocode:
                    Store ack(_,_,_) in an ack list.
                    If ack(n,v (?) TODO ,_) is received from a MAJORITY of acceptors, then send ACCEPT(v,n)
                    If ack(n,v',n') is received at any time (meaning a value was accepted already)
                        override v to use v', and send ACCEPT(v',N), where N is the HIGHEST sequence number seen
                    """
                    (n1,v,n2) = message["MESSAGE"]
                    if DEBUG: print(f"Ack received at {self.role} {self.uid}: {(n1,v,n2)}")
                    min_majority = math.floor(len(self.acceptors)/2) + 1 # The minimum number of acceptors that constitutes a majority
                    self.acks.append((n1,v,n2))
                    
                    # Check if majority has been received for (n1, v, _)
                    # TODO review
                    n1_ack_list = list(filter(lambda x: (x[0]==n1), self.acks))
                    print("Phase 2.1",min_majority,self.acks,n1_ack_list)
                    if len(n1_ack_list) >= min_majority:
                        print("MAJORITY ACHIEVED BY PROPOSER - SENDING ACCEPT REQUEST TO ALL ACCEPTORS")
                        # Find if any value was already accepted
                        accepted = []
                        for ack in self.acks:
                            if ack[2] != "_":
                                pass # TODO
                                # This means there was an n' that was accepted
                            else:
                                # Submit v and n to the acceptors
                                accept_req = (n1,v)
                                self.udp_multicast("ACCEPT",accept_req,self.acceptors)
                    # TODO needs v of most recently accepted value



                if message["HEADER"] == "ACCEPT":
                    if self.role != "ACCEPTOR":
                        raise Exception("Message sent to incorrect recipient")
                    """
                    The recipient of this message initiates Paxos phase 2.2
                    An ACCEPT(v,n) is accepted unless there is a promise to a sequence number greater than n.
                    Pseudocode:
                    If ack(n,_,_) or ack(_,_,n) found in promise list, ignore.
                    Else accept v and n, and add to the accept list.
                    Short time wait? TODO
                    Forward values to learner
                    """
                    # Reminder - proposals and accept requests are (v,n), acks are (n1,v,n2) format
                    print(f"Accept request received by a {self.role} (ID {self.uid}): {message}")
                    (v,n) = message["MESSAGE"]
                    # Check if a promise has (v1,n1), where n1 < n (don't accept in this case)
                    greater_promises = list(filter(lambda x: x[1] > n, self.promises))
                    if len(greater_promises) == 0:
                        # Send to the learner since no greater promises were made
                        self.udp_multicast("LEARN",(v,n),self.learners) # TODO also multicast to proposers
                        print(f"{(v,n)} HAS BEEN ACCEPTED")


                if message["HEADER"] == "LEARN":
                    if self.role != "LEARNER":
                        raise Exception("Message sent to incorrect recipient")
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
                    # TODO review
                    acceptance_list = list(filter(lambda x: (x[1]==n), self.acceptances))
                    print(len(acceptance_list),min_majority)
                    if len(acceptance_list) >= min_majority:
                        print("MAJORITY ACHIEVED BY ACCEPTORS.")
                        self.udp_multicast("SET",v,self.cli_nodes)
                    # TODO needs v of most recently accepted value 
                    

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
                    self.message_queue.append(message) # TODO mutex
            finally:
                udp_socket.close()
                    
