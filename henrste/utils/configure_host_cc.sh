#!/bin/bash

# this scripts sets congestion control on a host

if [ -z $3 ]; then
    echo "Usage: $0 <host> <tcp_congestion_control> <tcp_ecn>"
    exit 1
fi

host=$1
tcp_congestion_control=$2
tcp_ecn=$3

ssh $host '
    if [ -f /proc/sys/net/ipv4/tcp_congestion_control ]; then
        sudo sysctl -q -w net.ipv4.tcp_congestion_control='$tcp_congestion_control'
    else
        # we are on docker
        . /tmp/testbed-vars-local.sh
        if ip a show $IFACE_AQM | grep -q 10.25.1.; then
            # on client
            ip route replace 10.25.2.0/24 via 10.25.1.2 dev $IFACE_AQM congctl '$tcp_congestion_control'
            ip route replace 10.25.3.0/24 via 10.25.1.2 dev $IFACE_AQM congctl '$tcp_congestion_control'
        else
            # on server
            ip_prefix=$(ip a show $IFACE_AQM | grep "inet 10" | awk "{print \$2}" | sed "s/\.[0-9]\+\/.*//")
            ip route replace 10.25.1.0/24 via ${ip_prefix}.2 dev $IFACE_AQM congctl '$tcp_congestion_control'
        fi
    fi
    sudo sysctl -q -w net.ipv4.tcp_ecn='$tcp_ecn
