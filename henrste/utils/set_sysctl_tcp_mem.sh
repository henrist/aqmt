#!/bin/sh
# syntax: ./set_sysctl_tcp_mem.sh [maximum_window_size]

# default values on Henrik's Simula-machine:
# net.ipv4.tcp_rmem = 4096        87380   6291456
# net.ipv4.tcp_wmem = 4096        16384   4194304
# net.core.netdev_max_backlog = 1000
# net.core.wmem_max = 212992
#
# from testing, without tso/gso, and with 1448 mss, the following has been
# shown:
# - tcp_rmem has to be double of the maximum receiver window * mss
# - tcp_wmem has to be tripple of the maximum packets in flight * mss
#
# The default values gives:
# - wmem=4194304: maximum tcp window of 965 (4194304 / 1448 / 3)
# - rmem=6921456: maximum tcp window of 4780 (6921456 / 1448)

if [ -f /.dockerenv ]; then
    echo "Don't run this inside Docker"
    exit 1
fi

if [ $(id -u) -ne 0 ]; then
    echo "Run this with sudo or as root"
    exit 1
fi

if [ -n "$1" ]; then
    max_window=$1
    rmem=$(($max_window * 1448 * 2))
    wmem=$(($max_window * 1448 * 3))
else
    # no argument will reset to "default"
    rmem=6291456
    wmem=4194304
fi

echo "Setting rmem and wmem locally"
sysctl -w net.ipv4.tcp_rmem="4096 87380 $rmem"
sysctl -w net.ipv4.tcp_wmem="4096 16384 $wmem"

if [ -n "$IP_CLIENTA_MGMT" ]; then
    for ip in $IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT; do
        echo "Setting rmem and wmem on $ip"
        ssh root@$ip "
            sysctl -w net.ipv4.tcp_rmem='4096 87380 $rmem'
            sysctl -w net.ipv4.tcp_wmem='4096 16384 $wmem'"
    done
fi

echo "Maximum window size is now approx. (using 1448 sized segments):"
echo "   $((rmem / 1448 / 2)) packets for receiving side"
echo "   $((wmem / 1448 / 3)) packets for sending side"
