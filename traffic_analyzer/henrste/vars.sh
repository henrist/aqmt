#!/bin/bash

tc=/home/testbed/dual-queue-aqm/iproute2-3.16.0/tc/tc

clients_iface=enp2s0f1
servera_iface=enp2s0f3
serverb_iface=enp2s0f2

servera_ip=10.0.3.201
serverb_ip=10.0.2.200

servera_aqm_ip=10.0.3.100
serverb_aqm_ip=10.0.2.100
