#!/bin/bash
set -e

# we mount ssh setup in a specific template directory
# now we copy this so it is effective
mkdir -p /root/.ssh/
cp /ssh-template/* /root/.ssh/
chown -R root:root /root/.ssh/
chmod 600 /root/.ssh/*

# arp config is done to avoid arp lookups that causes loss

disable_so() {
    iface=$1
    # disable segmentation offload
    # see http://rtodto.net/generic_segmentation_offload_and_wireshark/
    (set -x && ethtool -K $iface gso off)
    (set -x && ethtool -K $iface tso off)
}

setup_client() {
    local iface=$(ip route show to 10.25.1.0/24 | awk '{print $3}')
    echo "Adding route to servers through aqm-machine"
    (set -x && ip route add 10.25.2.0/24 via 10.25.1.2 dev $iface)
    (set -x && ip route add 10.25.3.0/24 via 10.25.1.2 dev $iface)
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.1.2 02:42:0a:19:01:02)

    disable_so $iface

    echo "export IFACE_AQM=$iface" >/aqmt-vars-local.sh
}

setup_server() {
    local iface=$(ip route show to ${1}.0/24 | awk '{print $3}')

    echo "Adding route to clients through aqm-machine"
    (set -x && ip route add 10.25.1.0/24 via ${1}.2 dev $iface)
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)

    disable_so $iface

    (set -x && arp -i $iface -s ${1}.2 02:42:0a:19:0${1/*.}:02)

    echo "export IFACE_AQM=$iface" >/aqmt-vars-local.sh

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
    echo "export IFACE_MGMT=$iface" >/aqmt-vars-local.sh

    local iface=$(ip route show to 10.25.1.0/24 | awk '{print $3}')
    echo "export IFACE_CLIENTS=$iface" >>/aqmt-vars-local.sh
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.1.11 02:42:0a:19:01:0b)
    (set -x && arp -i $iface -s 10.25.1.12 02:42:0a:19:01:0c)

    disable_so $iface

    local iface=$(ip route show to 10.25.2.0/24 | awk '{print $3}')
    echo "export IFACE_SERVERA=$iface" >>/aqmt-vars-local.sh
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.2.21 02:42:0a:19:02:15)

    disable_so $iface

    local iface=$(ip route show to 10.25.3.0/24 | awk '{print $3}')
    echo "export IFACE_SERVERB=$iface" >>/aqmt-vars-local.sh
    (set -x && tc qdisc add dev $iface root handle 1: pfifo_fast)
    (set -x && ip link set $iface txqueuelen 1000)
    (set -x && arp -i $iface -s 10.25.2.31 02:42:0a:19:03:1f)

    disable_so $iface

    # wait a bit for other nodes to come up before we try to connect
    sleep 2

    names=(CLIENTA CLIENTB SERVERA SERVERB)
    nets=(10.25.1.0/24 10.25.1.0/24 10.25.2.0/24 10.25.3.0/24)
    for i in ${!names[@]}; do
        (
            . /aqmt-vars.sh
            local ip_name="IP_${names[$i]}"
            local iface
            iface=$(ssh ${!ip_name} "ip route show to ${nets[$i]} | awk '{print \$3}'")
            echo "export IFACE_ON_${names[$i]}=$iface" >>/aqmt-vars-local.sh
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
