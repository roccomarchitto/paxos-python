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
        PROPOSERS = mode_counts[0]
        ACCEPTORS = mode_counts[1]
        LEARNERS = mode_counts[2]
        self.host_info = hosts[uid] # host_info is a list [hostname, port, consensus or client]
        print(f'\nCONLIB CALLED for {uid}:\t{PROPOSERS},{ACCEPTORS},{LEARNERS},{self.host_info}')

    def InitializeNode(self) -> None:
        pass

    def Run(self) -> None:
        pass

    def CleanupNode(self) -> None:
        pass


    """
    Network interface methods
    """    
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
        with socket(AF.INET, SOCK_DGRAM) as udp_socket:
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
                    
