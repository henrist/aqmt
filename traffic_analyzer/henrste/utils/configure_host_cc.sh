#!/bin/bash

# this scripts sets congestion control on a host

if [ -z $3 ]; then
    echo "Syntax: $0 <host> <tcp_congestion_control> <tcp_ecn>"
    exit 1
fi

host=$1
tcp_congestion_control=$2
tcp_ecn=$3

ssh $host "
    sudo sysctl -q -w net.ipv4.tcp_congestion_control=$tcp_congestion_control;
    sudo sysctl -q -w net.ipv4.tcp_ecn=$tcp_ecn"
