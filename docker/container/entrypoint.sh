#!/bin/bash

# arp config is done to avoid arp lookups that causes loss

setup_client() {
    local iface=$(ip route show to 10.25.1.0/24 | awk '{print $3}')
    echo "Adding route to servers through aqm-machine"
    (set -x && ip route add 10.25.2.0/24 via 10.25.1.2 dev $iface)
    (set -x && ip route add 10.25.3.0/24 via 10.25.1.2 dev $iface)
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.1.2 02:42:0a:19:01:02)

    echo "export IFACE_AQM=$iface" >/tmp/testbed-vars-local.sh
}

setup_server() {
    local iface=$(ip route show to ${1}.0/24 | awk '{print $3}')

    echo "Adding route to clients through aqm-machine"
    (set -x && ip route add 10.25.1.0/24 via ${1}.2 dev $iface)
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)

    (set -x && arp -i $iface -s ${1}.2 02:42:0a:19:0${1/*.}:02)

    echo "export IFACE_AQM=$iface" >/tmp/testbed-vars-local.sh

    #echo "Adding route to other servers through aqm-machine"
    #if [ "$(ip route show to 10.25.2.0/24)" == "" ]; then
    #    (set -x && ip route add 10.25.2.0/24 via ${1}.2 dev $iface)
    #else
    #    (set -x && ip route add 10.25.3.0/24 via ${1}.2 dev $iface)
    #fi
}

setup_aqm() {
    echo "Setting up AQM-variables"

    local iface=$(ip route show to 10.25.0.0/24 | awk '{print $3}')
    echo "export IFACE_MGMT=$iface" >/tmp/testbed-vars-local.sh

    local iface=$(ip route show to 10.25.1.0/24 | awk '{print $3}')
    echo "export IFACE_CLIENTS=$iface" >>/tmp/testbed-vars-local.sh
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.1.11 02:42:0a:19:01:0b)

    local iface=$(ip route show to 10.25.2.0/24 | awk '{print $3}')
    echo "export IFACE_SERVERA=$iface" >>/tmp/testbed-vars-local.sh
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.2.21 02:42:0a:19:02:15)

    local iface=$(ip route show to 10.25.3.0/24 | awk '{print $3}')
    echo "export IFACE_SERVERB=$iface" >>/tmp/testbed-vars-local.sh
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.2.31 02:42:0a:19:03:1f)

    names=(CLIENTA CLIENTB SERVERA SERVERB)
    nets=(10.25.1.0/24 10.25.1.0/24 10.25.2.0/24 10.25.3.0/24)
    for i in ${!names[@]}; do
        (
            . /tmp/testbed-vars.sh
            local ip_name="IP_${names[$i]}"
            local iface=$(ssh ${!ip_name} "ip route show to ${nets[$i]} | awk '{print \$3}'")
            echo "export IFACE_ON_${names[$i]}=$iface" >>/tmp/testbed-vars-local.sh
        )
    done
}

# add routes through aqm-machine
if [ "$(ip addr show to 10.25.0.2)" == "" ]; then
    if ip a | grep -q "inet 10.25.1."; then
        setup_client
    elif ip a | grep -q "inet 10.25.2."; then
        setup_server 10.25.2
    elif ip a | grep -q "inet 10.25.3."; then
        setup_server 10.25.3
    fi
else
    setup_aqm
fi

exec "$@"
