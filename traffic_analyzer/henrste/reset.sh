#!/bin/bash

# need to reset qdisc on the aqm machine
for i in 1 2 3; do
    sudo tc qdisc del dev enp2s0f$i root 2>/dev/null
done

# need to reset congestion control on the clients and servers
for remote in client-a client-b server-a server-b; do
    ssh $remote '
        sudo sysctl -q -w net.ipv4.tcp_congestion_control=cubic;
        sudo sysctl -q -w net.ipv4.tcp_ecn=2'
done
