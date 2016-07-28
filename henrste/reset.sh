#!/bin/bash

# need to reset qdisc on the aqm machine
for dev in $IFACE_CLIENTS $IFACE_SERVERA $IFACE_SERVERB; do
    sudo tc qdisc del dev $dev root 2>/dev/null
done

# need to reset congestion control on the clients and servers
for remote in $IP_CLIENTA_MGMT $IP_CLIENTb_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT; do
    ssh $remote '
        sudo sysctl -q -w net.ipv4.tcp_congestion_control=cubic;
        sudo sysctl -q -w net.ipv4.tcp_ecn=2'
done
