#!/bin/bash

cd "$(dirname $(readlink -f $BASH_SOURCE))"

. ../common.sh

for host in CLIENTA CLIENTB SERVERA SERVERB; do
    name="IP_${host}_MGMT"
    ./configure_host_cc.sh ${!name} cubic 2
done

# reset qdisc at client side
tc qdisc del dev $IFACE_CLIENTS root 2>/dev/null || true
tc qdisc add dev $IFACE_CLIENTS root handle 1: pfifo_fast 2>/dev/null || true

# reset qdisc at server side
for iface in $IFACE_SERVERA $IFACE_SERVERB; do
    tc qdisc del dev $iface root 2>/dev/null || true
    tc qdisc add dev $iface root handle 1: pfifo_fast 2>/dev/null || true
done

hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT)
ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB $IFACE_ON_SERVERA $IFACE_ON_SERVERB)

for i in ${!hosts[@]}; do
    ssh ${hosts[$i]} "
        sudo tc qdisc del dev ${ifaces[$i]} root 2>/dev/null || true
        sudo tc qdisc add dev ${ifaces[$i]} root handle 1: pfifo_fast 2>/dev/null || true"
done
