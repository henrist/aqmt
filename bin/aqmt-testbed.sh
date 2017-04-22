#!/bin/bash

# this file contains all code that is used to actually modify the testbed
# parameters on the different machines
#
# it acts as an abstraction layer on top of the testbed
#
# it handles both setup in the docker environment as well as on a real testbed
# as the variables for the testbed is stored seperately

. "$(dirname $(readlink -f $BASH_SOURCE))/aqmt-vars.sh"

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

configure_host_cc() {(set -e
    local host=$1
    local tcp_congestion_control=$2
    local tcp_ecn=$3

    local feature_ecn=""
    if [ "$tcp_ecn" == "1" ]; then
        feature_ecn=" features ecn"
    fi

    # the 10.25. range belongs to the Docker setup
    # it needs to use congctl for a per route configuration
    # (congctl added in iproute2 v4.0.0)
    ssh root@$host '
        set -e
        if [ -f /proc/sys/net/ipv4/tcp_congestion_control ]; then
            sysctl -q -w net.ipv4.tcp_congestion_control='$tcp_congestion_control'
        else
            # we are on docker
            . /aqmt-vars-local.sh
            if ip a show $IFACE_AQM | grep -q 10.25.1.; then
                # on client
                ip route replace 10.25.2.0/24 via 10.25.1.2 dev $IFACE_AQM congctl '$tcp_congestion_control$feature_ecn'
                ip route replace 10.25.3.0/24 via 10.25.1.2 dev $IFACE_AQM congctl '$tcp_congestion_control$feature_ecn'
            else
                # on server
                ip_prefix=$(ip a show $IFACE_AQM | grep "inet 10" | awk "{print \$2}" | sed "s/\.[0-9]\+\/.*//")
                ip route replace 10.25.1.0/24 via ${ip_prefix}.2 dev $IFACE_AQM congctl '$tcp_congestion_control$feature_ecn'
            fi
        fi
        sysctl -q -w net.ipv4.tcp_ecn='$tcp_ecn
) || (echo -e "\nERROR: Failed setting cc $2 (ecn = $3) on node $1\n"; exit 1)}

configure_clients_edge_aqm_node() {(set -e
    local testrate=$1
    local rtt=$2
    local aqm_name=$3
    local aqm_params=$4
    local netem_params=$5  # optional

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # htb = hierarchy token bucket - used to limit bandwidth
    # netem = used to simulate delay (link distance)

    if [ $rtt -gt 0 ]; then
        if tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc netem 2:"; then
            tc qdisc change dev $IFACE_CLIENTS handle 2: netem delay ${delay}ms $netem_params
            tc class change dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate
        else
            tc qdisc  del dev $IFACE_CLIENTS root 2>/dev/null || true
            tc qdisc  add dev $IFACE_CLIENTS root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
            tc filter add dev $IFACE_CLIENTS parent 1:0 protocol ip prio 1 u32 match ip src $IP_AQM_C flowid 1:1
            tc qdisc  add dev $IFACE_CLIENTS parent 1:2 handle 2:  netem delay ${delay}ms $netem_params
            tc qdisc  add dev $IFACE_CLIENTS parent 2: handle 3: htb default 10
            tc class  add dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate   #burst 1516
        fi
    else
        if ! tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc netem 2:" && \
                tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc htb 3:"; then
            tc class change dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate
        else
            tc qdisc  del dev $IFACE_CLIENTS root 2>/dev/null || true
            tc qdisc  add dev $IFACE_CLIENTS root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
            tc filter add dev $IFACE_CLIENTS parent 1:0 protocol ip prio 1 u32 match ip src $IP_AQM_C flowid 1:1
            tc qdisc  add dev $IFACE_CLIENTS parent 1:2 handle 3: htb default 10
            tc class  add dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate   #burst 1516
        fi
    fi

    if [ -n "$aqm_name" ]; then
        # update params if possible
        if tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc $aqm_name 15:"; then
            tc qdisc change dev $IFACE_CLIENTS handle 15: $aqm_name $aqm_params
            echo "Updated params on existing aqm"
        else
            tc qdisc  add dev $IFACE_CLIENTS parent 3:10 handle 15: $aqm_name $aqm_params
        fi
    fi
) || (echo -e "\nERROR: Failed configuring AQM clients edge (aqm = $3)\n"; exit 1)}

configure_clients_node() {(set -e
    local rtt=$1
    local netem_params=$2  # optional

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # netem = used to simulate delay (link distance)

    if [ $rtt -gt 0 ]; then
        hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT)
        ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB)
        for i in ${!hosts[@]}; do
            ssh root@${hosts[$i]} "
                set -e
                # if possible update the delay rather than destroying the existing qdisc
                if tc qdisc show dev ${ifaces[$i]} | grep -q 'qdisc netem 12:'; then
                    tc qdisc change dev ${ifaces[$i]} handle 12: netem delay ${delay}ms $netem_params
                else
                    tc qdisc  del dev ${ifaces[$i]} root 2>/dev/null || true
                    tc qdisc  add dev ${ifaces[$i]} root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
                    tc qdisc  add dev ${ifaces[$i]} parent 1:2 handle 12: netem delay ${delay}ms $netem_params
                    tc filter add dev ${ifaces[$i]} parent 1:0 protocol ip prio 1 u32 match ip dst $IP_AQM_C flowid 1:1
                fi"
        done
    else
        # no delay: force pfifo_fast
        hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT)
        ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB)
        for i in ${!hosts[@]}; do
            ssh root@${hosts[$i]} "
                set -e
                # skip if already set up
                if ! tc qdisc show dev ${ifaces[$i]} | grep -q 'qdisc pfifo_fast 1:'; then
                    tc qdisc del dev ${ifaces[$i]} root 2>/dev/null || true
                    tc qdisc add dev ${ifaces[$i]} root handle 1: pfifo_fast 2>/dev/null || true
                fi"
        done
    fi
) || (echo -e "\nERROR: Failed configuring client nodes\n"; exit 1)}

configure_clients_edge() {(set -e
    local testrate=$1
    local rtt=$2
    local aqm_name=$3
    local aqm_params=$4
    local netem_params=$5  # optional

    configure_clients_edge_aqm_node $testrate $rtt $aqm_name "$aqm_params" "$netem_params"
    configure_clients_node $rtt "$netem_params"
)}

configure_server_edge() {(set -e
    local ip_server_mgmt=$1
    local ip_aqm_s=$2
    local iface_server=$3
    local iface_on_server=$4
    local rtt=$5
    local netem_params=$6  # optional

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # put traffic in band 1 by default
    # delay traffic in band 1
    # filter traffic from aqm node itself into band 0 for priority and no delay
    if tc qdisc show dev $iface_server | grep -q 'qdisc netem 12:'; then
        tc qdisc change dev $iface_server handle 12: netem delay ${delay}ms $netem_params
    else
        tc qdisc  del dev $iface_server root 2>/dev/null || true
        tc qdisc  add dev $iface_server root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
        tc qdisc  add dev $iface_server parent 1:2 handle 12: netem delay ${delay}ms $netem_params
        tc filter add dev $iface_server parent 1:0 protocol ip prio 1 u32 match ip src $ip_aqm_s flowid 1:1
    fi

    ssh root@$ip_server_mgmt "
        set -e
        if tc qdisc show dev $iface_on_server | grep -q 'qdisc netem 12:'; then
            tc qdisc change dev $iface_on_server handle 12: netem delay ${delay}ms $netem_params
        else
            tc qdisc  del dev $iface_on_server root 2>/dev/null || true
            tc qdisc  add dev $iface_on_server root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
            tc qdisc  add dev $iface_on_server parent 1:2 handle 12: netem delay ${delay}ms $netem_params
            tc filter add dev $iface_on_server parent 1:0 protocol ip prio 1 u32 match ip dst $ip_aqm_s flowid 1:1
        fi"
) || (echo -e "\nERROR: Failed configuring server edge for server $1\n"; exit 1)}

reset_aqm_client_edge() {(set -e
    # reset qdisc at client side
    tc qdisc del dev $IFACE_CLIENTS root 2>/dev/null || true
    tc qdisc add dev $IFACE_CLIENTS root handle 1: pfifo_fast 2>/dev/null || true
)}

reset_aqm_server_edge() {(set -e
    # reset qdisc at server side
    for iface in $IFACE_SERVERA $IFACE_SERVERB; do
        tc qdisc del dev $iface root 2>/dev/null || true
        tc qdisc add dev $iface root handle 1: pfifo_fast 2>/dev/null || true
    done
)}

reset_host() {(set -e
    local host=$1
    local iface=$2 # the iface is the one that test traffic to aqm is going on
                   # e.g. $IFACE_ON_CLIENTA
    ssh root@$host "
        set -e
        tc qdisc del dev $iface root 2>/dev/null || true
        tc qdisc add dev $iface root handle 1: pfifo_fast 2>/dev/null || true"
)}

reset_all_hosts_edge() {(set -e
    hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT)
    ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB $IFACE_ON_SERVERA $IFACE_ON_SERVERB)

    for i in ${!hosts[@]}; do
        reset_host ${hosts[$i]} ${ifaces[$i]}
    done
)}

reset_all_hosts_cc() {(set -e
    for host in CLIENTA CLIENTB SERVERA SERVERB; do
        name="IP_${host}_MGMT"
        configure_host_cc ${!name} cubic 2
    done
)}

set_offloading() {(set -e
    onoff=$1

    hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT)
    ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB $IFACE_ON_SERVERA $IFACE_ON_SERVERB)

    for i in ${!hosts[@]}; do
        ssh root@${hosts[$i]} "
            set -e
            ethtool -K ${ifaces[$i]} gro $onoff
            ethtool -K ${ifaces[$i]} gso $onoff
            ethtool -K ${ifaces[$i]} tso $onoff"
    done

    for iface in $IFACE_CLIENTS $IFACE_SERVERA $IFACE_SERVERB; do
        sudo ethtool -K $iface gro $onoff
        sudo ethtool -K $iface gso $onoff
        sudo ethtool -K $iface tso $onoff
    done
)}

kill_all_traffic() {(set -e
    hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT)

    for host in ${hosts[@]}; do
        ssh root@$host '
            set -e
            killall -9 iperf 2>/dev/null || :
            killall -9 greedy 2>/dev/null || :'
    done
)}

get_host_cc() {(set -e
    local host=$1

    # see configure_host_cc for more details on setup

    ssh root@$host '
        set -e
        if [ -f /proc/sys/net/ipv4/tcp_congestion_control ]; then
            sysctl -n net.ipv4.tcp_congestion_control
            sysctl -n net.ipv4.tcp_ecn
        else
            # we are on docker
            . /aqmt-vars-local.sh
            if ip a show $IFACE_AQM | grep -q 10.25.1.; then
                # on client
                route=10.25.2.0/24
            else
                route=10.25.1.0/24
            fi

            ip route show $route | awk -F"congctl " "{print \$2}" | cut -d" " -f1
            ip route show $route | grep -q "ecn" && echo "1" || echo "2"
        fi'
)}

get_aqm_options() {(set -e
    local aqm_name=$1

    if [ -n "$aqm_name" ]; then
        tc qdisc show dev $IFACE_CLIENTS | grep "$aqm_name" | sed 's/.*parent [0-9:]\+ //'
    else
        echo '(no aqm)'
    fi
)}

# method that will abort the script if we are not on the aqm-machine
require_on_aqm_node() {
    if ! [[ $(ip addr show to $IP_AQM_C) ]]; then
        echo "The program must be run on the AQM-machine"
        exit 1
    fi
}

# method that will abort the script if we are on the aqm-machine
require_not_on_aqm_node() {
    if [[ $(ip addr show to $IP_AQM_C) ]]; then
        echo "The program cannot be run on the AQM-machine"
        exit 1
    fi
}
