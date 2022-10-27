#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implements the ClientNode class.
Clients wait for proposers to tell them they are accepting requests.
Then clients submit their proposed values.
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

DEBUG = False

class ClientNode():
    def __init__(self, mode_counts: tuple[int], hosts: List[List[str]], uid: int, v: int, proposer: int):
        """
        Params:
            mode_counts (tuple[int]): tuple (proposers,acceptors,learners) of the counts for the 3 different modes
            hosts (List[Lint[int]]): List of lists [hostname, port, consensus or client] for the hosts
            uid (int): Unique identifier for this host
            v (int): The value the client wants to set the global variable to
            proposer (int): The proposer ID the client wants to send to (note that this is calculated by 
                            proposer index = (desired ID) modulo (length of proposer))
        """
        if DEBUG: print(f"Client launched with v={v}")
        self.v = int(v)
        PROPOSERS = mode_counts[0]
        ACCEPTORS = mode_counts[1]
        LEARNERS = mode_counts[2]
        self.hosts = hosts
        self.host_info = hosts[uid] # host_info is a list [hostname, port, consensus or client]
        self.uid = uid
        self.proposer = proposer
        self.port = int(self.host_info[1])
        if DEBUG: print(f'\nCLILIB CALLED for {uid} w/ val {self.v}:\t{PROPOSERS},{ACCEPTORS},{LEARNERS},{self.host_info}')
        self.chosen_proposer = -1
        #self.udp_listen_for_proposers()
    
    def Set(self, VAL) -> None:
        """
        Forwards VAL to a proposer for use in Paxos
        """
        time.sleep(0.1) # Wait a short time for other nodes to prep
        VAL = int(VAL)
        assert(self.v == VAL)
        #print(f"Client {self.uid} forward VALUE {VAL} to proposer {self.hosts[self.chosen_proposer]}")
        self.udp_send("FWD",VAL,self.hosts[self.chosen_proposer][0],self.hosts[self.chosen_proposer][1])
        self.wait() # Wait for a value to arrive
    
    def wait(self) -> None:
        """
        Waits for a decided on value to arrive
        """
        # TODO - while loop?
        with socket(AF_INET, SOCK_DGRAM) as udp_socket:
            try:
                udp_socket.bind(("", self.port))
                while True:
                    # Receive and deserialize message
                    # Message is a dictionary with keys HEADER, MESSAGE, RECIPIENT, PORT, and SENDERID
                    message, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                    message = pickle.loads(message)
                    if message["HEADER"] == "SET":
                        chosen_value = message["MESSAGE"]
                        #time.sleep(1)
                        print("Final message received by client from learner:",chosen_value)
                        break
                    else:
                        raise Exception("Message sent before start to client, or corrupted/incorrect.")
                
            finally:
                udp_socket.close()

    def InitializeNode(self) -> None:
        """
        Waits for proposers to say they are ready for proposals.
        """
        with socket(AF_INET, SOCK_DGRAM) as udp_socket:
            try:
                udp_socket.bind(("", self.port))
                # Receive and deserialize message
                # Message is a dictionary with keys HEADER, MESSAGE, RECIPIENT, and PORT
                message, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                message = pickle.loads(message)
                if message["HEADER"] == "START":
                    roles_tuple = message["MESSAGE"]
                    proposers = roles_tuple[0]
                    #print("Proposers list received:",proposers)
                    
                    proposer_idx = self.proposer % len(proposers)
                    #print("Chosen proposer idx:",proposer_idx)
                    self.chosen_proposer = proposers[proposer_idx]
                    #print(self.chosen_proposer)

                    #print("Client now preparing to submit proposals...")
                else:
                    raise Exception("Message sent before start to client, or corrupted/incorrect.")
                
            finally:
                udp_socket.close()

    def CleanupNode(self) -> None:
        """
        When a consensus is reached, at least one client will progress to call CleanupNode.
        This will signal all processes to shut down.
        """
        time.sleep(5)
        # Multicast TERM messages
        for host in self.hosts:
            self.udp_send("TERM","","localhost",host[1])
        os._exit(0)

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
                        'PORT': int(port)
                    }
        message = pickle.dumps(message)

        # Send the message over UDP
        with socket(AF_INET, SOCK_DGRAM) as udp_socket:
            udp_socket.sendto(message, (recipient, int(port)))
    