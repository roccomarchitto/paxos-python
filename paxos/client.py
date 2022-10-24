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
import pickle
import time
import random

BUFFER_SIZE = 4096


class ClientNode():
    def __init__(self, mode_counts: tuple[int], hosts: List[List[str]], uid: int, v: int):
        """
        Params:
            mode_counts (tuple[int]): tuple (proposers,acceptors,learners) of the counts for the 3 different modes
            hosts (List[Lint[int]]): List of lists [hostname, port, consensus or client] for the hosts
            uid (int): Unique identifier for this host
            v (int): The value the client wants to set the global variable to
        """
        print(f"Client launched with v={v}")
        self.v = v
        PROPOSERS = mode_counts[0]
        ACCEPTORS = mode_counts[1]
        LEARNERS = mode_counts[2]
        self.host_info = hosts[uid] # host_info is a list [hostname, port, consensus or client]
        self.port = int(self.host_info[1])
        print(f'\nCLILIB CALLED for {uid} w/ val {self.v}:\t{PROPOSERS},{ACCEPTORS},{LEARNERS},{self.host_info}')

        self.udp_listen_for_proposers()
    
    def udp_listen_for_proposers(self) -> None:
        """
        Waits for proposers to say they are ready for proposals.
        """
        # TODO - wait for *all* proposers
        with socket(AF_INET, SOCK_DGRAM) as udp_socket:
            try:
                udp_socket.bind(("", self.port))
                while True:
                    # Receive and deserialize messages
                    # Message is a dictionary with keys HEADER, MESSAGE, RECIPIENT, and PORT
                    message, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                    message = pickle.loads(message)

                    # TODO: Handlem essage
                    print("Message received:", message)
            finally:
                udp_socket.close()