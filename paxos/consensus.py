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
        self.hosts = hosts
        self.host_info = hosts[uid] # host_info is a list [hostname, port, consensus or client]
        self.uid = uid
        self.port = int(self.host_info[1])
        self.hostname = self.host_info[0]
        self.type = self.host_info[2] # either con for consensus node or cli for client node
        self.role = "" # To be populated; either PROPOSER, ACCEPTOR, or LEARNER
        self.is_leader = False
        
        # Detect if leader w/ list of consensus nodes
        self.con_nodes = list(filter(lambda x: x[2] == "con", self.hosts))
        if self.uid == len(self.con_nodes)-1:
            self.is_leader = True
        #print(f'\nCONLIB CALLED for {uid}:\t{PROPOSERS},{ACCEPTORS},{LEARNERS},{self.host_info}')

        # List of client nodes
        self.cli_nodes = list(filter(lambda x: x[2] == "cli", self.hosts))

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
                idx += 1
            for i in range(ACCEPTORS):
                #print(f"Node {idx} is an ACCEPTOR")
                self.udp_send("ROLE","ACCEPTOR",self.hosts[idx][0],self.hosts[idx][1])
                idx += 1
            for i in range(LEARNERS):
                #print(f"Node {idx} is a LEARNER")
                self.udp_send("ROLE","LEARNER",self.hosts[idx][0],self.hosts[idx][1])
                idx += 1
            # By this setup, the n-1st node is always a learner (message gets lost, but that is OK)
            self.role = "LEARNER"
            print(f"Node {self.uid} has accepted role {self.role}")

            time.sleep(0.05)
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
                    print(f"Node {self.uid} has accepted role {self.role}")
                    #print(f"Message received @ {self.uid}:",message)
                        
                finally:
                    udp_socket.close()
            

    def Run(self) -> None:
        # First set up a listener thread for incoming messages
        print(f"Running {self.uid} as a {self.role}")

        # The leader should notify the clients to start sending proposals to proposers
        if (self.is_leader):
            self.udp_multicast("START","---",self.cli_nodes)
            print(self.cli_nodes)
        # TODO: Allow for choosing of a specific proposer
        

    def CleanupNode(self) -> None:
        pass


    """
    Network interface methods
    """
    def udp_multicast(self, header: str, message: str, group: List[List[str]]) -> None:
        # group is a list of hosts (lists) [[hostname,port,type],...]
        for rec in group:
            self.udp_send(header, message, rec[0], int(rec[1]))



    def udp_send(self, header: str, message: str, recipient: str, port: int) -> None:
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
                        'PORT': int(port)
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

                    #TODO: HANDLE MESSAGE
                    print("Message received:",message)
                    
            finally:
                udp_socket.close()
                    
