#!/bin/bash

. "$(dirname $(readlink -f $BASH_SOURCE))/vars.sh"

# run all tc and ip commands through sudo if needed
tc() {
    if [ $(id -u) -ne 0 ]; then
        sudo $tc "$@"
    else
        command $tc "$@"
    fi
}

ip() {
    if [ $(id -u) -ne 0 ]; then
        sudo ip "$@"
    else
        command ip "$@"
    fi
}

configure_host_cc() {
    local host=$1
    local tcp_congestion_control=$2
    local tcp_ecn=$3

    # the 10.25. range belongs to the Docker setup
    # it needs to use congctl for a per route configuration
    # (congctl added in iproute2 v4.0.0)
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
}

configure_clients_edge_aqm_node() {
    local testrate=$1
    local rtt=$2
    local aqm_name=$3
    local aqm_params=$4

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # htb = hierarchy token bucket - used to limit bandwidth
    # netem = used to simulate delay (link distance)

    if [ $rtt -gt 0 ]; then
        tc qdisc  del dev $IFACE_CLIENTS root 2>/dev/null || true
        tc qdisc  add dev $IFACE_CLIENTS root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
        tc filter add dev $IFACE_CLIENTS parent 1:0 protocol ip prio 1 u32 match ip src $IP_AQM_C flowid 1:1
        tc qdisc  add dev $IFACE_CLIENTS parent 1:2 handle 2:  netem delay ${delay}ms
        tc qdisc  add dev $IFACE_CLIENTS parent 2: handle 3: htb default 10
        tc class  add dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate   #burst 1516
    else
        tc qdisc  del dev $IFACE_CLIENTS root 2>/dev/null || true
        tc qdisc  add dev $IFACE_CLIENTS root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
        tc filter add dev $IFACE_CLIENTS parent 1:0 protocol ip prio 1 u32 match ip src $IP_AQM_C flowid 1:1
        tc qdisc  add dev $IFACE_CLIENTS parent 1:2 handle 3: htb default 10
        tc class  add dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate   #burst 1516
    fi

    if [ -n "$aqm_name" ]; then
        tc qdisc  add dev $IFACE_CLIENTS parent 3:10 $aqm_name $aqm_params
    fi
}

configure_clients_node() {
    local rtt=$1

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # netem = used to simulate delay (link distance)

    if [ $rtt -gt 0 ]; then
        hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT)
        ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB)
        for i in ${!hosts[@]}; do
            ssh ${hosts[$i]} "
                tc qdisc  del dev ${ifaces[$i]} root 2>/dev/null || true
                tc qdisc  add dev ${ifaces[$i]} root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
                tc qdisc  add dev ${ifaces[$i]} parent 1:2 handle 12: netem delay ${delay}ms;
                tc filter add dev ${ifaces[$i]} parent 1:0 protocol ip prio 1 u32 match ip dst $IP_AQM_C flowid 1:1"
        done
    else
        # no delay: force pfifo_fast
        hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT)
        ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB)
        for i in ${!hosts[@]}; do
            ssh ${hosts[$i]} "
                tc qdisc del dev ${ifaces[$i]} root 2>/dev/null || true
                tc qdisc add dev ${ifaces[$i]} root handle 1: pfifo_fast 2>/dev/null || true"
        done
    fi
}

configure_clients_edge() {
    local testrate=$1
    local rtt=$2
    local aqm_name=$3
    local aqm_params=$4

    configure_clients_edge_aqm_node $testrate $rtt $aqm_name "$aqm_params"
    configure_clients_node $rtt
}

configure_server_edge() {
    local ip_server_mgmt=$1
    local ip_aqm_s=$2
    local iface_server=$3
    local iface_on_server=$4
    local rtt=$5

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # put traffic in band 1 by default
    # delay traffic in band 1
    # filter traffic from aqm node itself into band 0 for priority and no delay
    tc qdisc  del dev $iface_server root 2>/dev/null || true
    tc qdisc  add dev $iface_server root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
    tc qdisc  add dev $iface_server parent 1:2 handle 12: netem delay ${delay}ms # todo: put "limit" ?
    tc filter add dev $iface_server parent 1:0 protocol ip prio 1 u32 match ip src $ip_aqm_s flowid 1:1

    ssh $ip_server_mgmt "
        sudo tc qdisc  del dev $iface_on_server root 2>/dev/null || true
        sudo tc qdisc  add dev $iface_on_server root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
        sudo tc qdisc  add dev $iface_on_server parent 1:2 handle 12: netem delay ${delay}ms;
        sudo tc filter add dev $iface_on_server parent 1:0 protocol ip prio 1 u32 match ip dst $ip_aqm_s flowid 1:1"
}

reset_aqm_client_edge() {
    # reset qdisc at client side
    tc qdisc del dev $IFACE_CLIENTS root 2>/dev/null || true
    tc qdisc add dev $IFACE_CLIENTS root handle 1: pfifo_fast 2>/dev/null || true
}

reset_aqm_server_edge() {
    # reset qdisc at server side
    for iface in $IFACE_SERVERA $IFACE_SERVERB; do
        tc qdisc del dev $iface root 2>/dev/null || true
        tc qdisc add dev $iface root handle 1: pfifo_fast 2>/dev/null || true
    done
}

reset_host() {
    local host=$1
    local iface=$2 # the iface is the one that test traffic to aqm is going on
                   # e.g. $IFACE_ON_CLIENTA
    ssh $host "
        tc qdisc del dev $iface root 2>/dev/null || true
        tc qdisc add dev $iface root handle 1: pfifo_fast 2>/dev/null || true"
}

reset_all_hosts_edge() {
    hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT)
    ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB $IFACE_ON_SERVERA $IFACE_ON_SERVERB)

    for i in ${!hosts[@]}; do
        reset_host ${hosts[$i]} ${ifaces[$i]}
    done
}

reset_all_hosts_cc() {
    for host in CLIENTA CLIENTB SERVERA SERVERB; do
        name="IP_${host}_MGMT"
        configure_host_cc ${!name} cubic 2
    done
}
