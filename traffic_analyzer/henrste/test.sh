#!/bin/bash
set -e
. common.sh

# interfaces:
#   enp2s0f1   To client A (10.0.1.211) and client B (10.0.1.210)
#   enp2s0f2   To server A (10.0.3.201)
#   enp2s0f3   To server B (10.0.2.200)


ctrlrate=400mbit
testrate=40mbit

aqm_name=dualq
aqm_params="l_thresh_us 1000 offset 0 l_slope 5 c_slope 4 l_smooth 0 c_smooth 5 l_power 1 c_power 2 l_shift 50"

rtt=10 # in ms


cleanup() {
    static_traffic_end client-a
    static_traffic_end client-b
}
trap cleanup EXIT


reset_configuration() {
    for host in client-a client-b server-a server-b; do
        configure_host_cc $host cubic 2
    done

    # reset qdisc at aqm-side
    tc qdisc del dev $clients_iface root 2>/dev/null || true

    # reset qdisc at server sides
    for iface in $servera_iface $serverb_iface; do
        tc qdisc del dev $iface root 2>/dev/null || true
    done

    ssh server-a sudo tc qdisc del dev enp3s0 root 2>/dev/null || true
    ssh server-b sudo tc qdisc del dev enp3s0 root 2>/dev/null || true
}


configure_host_cc() {
    host=$1
    tcp_congestion_control=$2
    tcp_ecn=$3

    ssh $host "
        sudo sysctl -q -w net.ipv4.tcp_congestion_control=$tcp_congestion_control;
        sudo sysctl -q -w net.ipv4.tcp_ecn=$tcp_ecn"
}


configure_clients_edge() {
    # htb = hierarchy token bucket - used to limit bandwidth
    # default traffic to the class with minor-id 5
    tc qdisc add dev $clients_iface root handle 1: htb default 5
    tc class add dev $clients_iface parent 1: classid 1:5 htb rate $ctrlrate
    tc class add dev $clients_iface parent 1: classid 1:10 htb rate $testrate burst 1516
    tc filter add dev $clients_iface protocol ip parent 1:0 prio 1 u32 match ip src $servera_ip flowid 1:10
    tc filter add dev $clients_iface protocol ip parent 1:0 prio 1 u32 match ip src $serverb_ip flowid 1:10

    # use the preferred aqm
    tc qdisc add dev $clients_iface parent 1:10 $aqm_name $aqm_params
}

configure_servers_edge() {
    # set up rtt on server edges
    for iface_and_ip in $servera_iface:$servera_aqm_ip \
                        $serverb_iface:$serverb_aqm_ip; do
        iface=$(echo $iface_and_ip | cut -f1 -d:)
        ip=$(echo $iface_and_ip | cut -f2 -d:)

        tc qdisc add dev $iface root handle 1: prio
        tc qdisc add dev $iface parent 1:1 handle 11: netem delay 0ms limit 40000
        tc qdisc add dev $iface parent 1:2 handle 12: netem delay $rtt.0ms limit 40000
        tc filter add dev $iface protocol ip parent 1:0 prio 1 u32 match ip src $ip classid 1:1
        tc filter add dev $iface protocol ip parent 1:0 prio 1 u32 match ip dst $ip classid 1:1
    done

}

start_traffic_analyzer() {
    #sudo ./ta $iface "${pcapfilter}" ${mainfolder}1000${foldername} 1000 $ipclass 250 &
    echo "doing nothing"
}


static_traffic_start() {
    client=$1 # host/ip
    server=$2 # host/ip

    ssh $server "nohup cat /dev/zero | nc -l 1234 >/dev/null 2>&1 &"
    ssh $client "nohup nc -d $server 1234 >/dev/null 2>&1 </dev/null &"
}

static_traffic_end() {
    client=$1 # host/ip

    ssh $client "killall nc"

    # the server will terminate automatically
}


reset_configuration

configure_clients_edge
configure_servers_edge

(sleep 2;
    static_traffic_start client-a server-a;
    static_traffic_start client-b server-b) &

./monitor.sh

#sleep 60
