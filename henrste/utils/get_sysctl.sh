#!/bin/sh

if [ -f /testbed-is-docker ]; then
    echo "Don't run this inside Docker"
    exit 1
fi

sysctl net.ipv4.tcp_rmem
sysctl net.ipv4.tcp_wmem
sysctl net.core.netdev_max_backlog
sysctl net.core.wmem_max
