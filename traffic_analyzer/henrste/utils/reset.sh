#!/bin/bash

cd "$(dirname $(readlink -f $BASH_SOURCE))"

. ../common.sh

for host in client-a client-b server-a server-b; do
    ./configure_host_cc.sh $host cubic 2
done

# reset qdisc at aqm-side
tc qdisc del dev $clients_iface root 2>/dev/null || true

# reset qdisc at server sides
for iface in $servera_iface $serverb_iface; do
    tc qdisc del dev $iface root 2>/dev/null || true
done

ssh server-a sudo tc qdisc del dev enp3s0 root 2>/dev/null || true
ssh server-b sudo tc qdisc del dev enp3s0 root 2>/dev/null || true
