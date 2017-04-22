#!/bin/sh

if [ -f /.dockerenv ]; then
    echo "Don't run this inside Docker"
    exit 1
fi

sysctl net.ipv4.tcp_rmem
sysctl net.ipv4.tcp_wmem
sysctl net.core.netdev_max_backlog
sysctl net.core.wmem_max

echo "Maximum window size is approx. (using 1448 sized segments):"
echo "   $(($(sysctl net.ipv4.tcp_rmem | awk '{ print $NF }') / 1448 / 2)) packets for receiving side"
echo "   $(($(sysctl net.ipv4.tcp_rmem | awk '{ print $NF }') / 1448 / 3)) packets for sending side"
