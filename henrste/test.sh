#!/bin/bash
set -e

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. common.sh

# interfaces:
#   enp2s0f1   To client A (10.0.1.211) and client B (10.0.1.210)
#   enp2s0f2   To server A (10.0.3.201)
#   enp2s0f3   To server B (10.0.2.200)


testrate=10mbit

rtt_servera=1000 # in ms
rtt_serverb=1000 # in ms

#aqm_name=dualq
#aqm_params="l_thresh_us 1000 offset 0 l_slope 5 c_slope 4 l_smooth 0 c_smooth 5 l_power 1 c_power 2 l_shift 50"


stop_traffic() {
    :
    utils/static_traffic.sh -k $IP_CLIENTA_MGMT $IP_SERVERA_MGMT $IP_SERVERA 1234
    utils/static_traffic.sh -k $IP_CLIENTB_MGMT $IP_SERVERB_MGMT $IP_SERVERB 1234
}


configure_clients_edge() {
    local testrate=$1

    tc qdisc  del dev $IFACE_CLIENTS root 2>/dev/null || true
    tc qdisc  add dev $IFACE_CLIENTS root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
    tc qdisc  add dev $IFACE_CLIENTS parent 1:2 handle 12: htb default 10
    tc class  add dev $IFACE_CLIENTS parent 12: classid 10 htb rate $testrate   #burst 1516
    tc filter add dev $IFACE_CLIENTS parent 1:0 protocol ip prio 1 u32 match ip src $IP_AQM_C flowid 1:1

    # htb = hierarchy token bucket - used to limit bandwidth
    # default traffic to the class with minor-id 5


    local delay=100
    ssh $IP_CLIENTA_MGMT "
        sudo tc qdisc  del dev $IFACE_ON_CLIENTA root 2>/dev/null || true
        sudo tc qdisc  add dev $IFACE_ON_CLIENTA root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
        sudo tc qdisc  add dev $IFACE_ON_CLIENTA parent 1:2 handle 12: netem delay ${delay}ms;
        sudo tc filter add dev $IFACE_ON_CLIENTA parent 1:0 protocol ip prio 1 u32 match ip dst $IP_AQM_C flowid 1:1"

    #tc qdisc add dev $IFACE_CLIENTS root handle 1: htb default 5
    #tc class add dev $IFACE_CLIENTS parent 1: classid 1:5 htb rate $ctrlrate
    #tc class add dev $IFACE_CLIENTS parent 1: classid 1:10 htb rate $testrate burst 1516
    #tc filter add dev $IFACE_CLIENTS protocol ip parent 1:0 prio 1 u32 match ip src $IP_SERVERA flowid 1:10
    #tc filter add dev $IFACE_CLIENTS protocol ip parent 1:0 prio 1 u32 match ip src $IP_SERVERB flowid 1:10

    # use the preferred aqm
    #tc qdisc add dev $IFACE_CLIENTS parent 12:10 $aqm_name $aqm_params

    #tc qdisc add dev $IFACE_CLIENTS parent 12:10 red limit 1000000 avpkt 1000 ecn #adaptive #bandwidth $testrate #10Mbit
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

#start_traffic_analyzer() {
    #sudo ./ta $iface "${pcapfilter}" ${mainfolder}1000${foldername} 1000 $ipclass 250 &
#}


trap stop_traffic EXIT

while true; do

echo "Starting traffic"
utils/reset.sh

configure_clients_edge $testrate

#utils/configure_host_cc.sh client-a dctcp 1
#utils/configure_host_cc.sh server-a dctcp 1
#utils/configure_host_cc.sh client-b dctcp 1
#utils/configure_host_cc.sh server-b dctcp 1

configure_server_edge $IP_SERVERA_MGMT $IP_AQM_SA $IFACE_SERVERA $IFACE_ON_SERVERA $rtt_servera
configure_server_edge $IP_SERVERB_MGMT $IP_AQM_SB $IFACE_SERVERB $IFACE_ON_SERVERB $rtt_serverb

#(sleep 2;
#    utils/static_traffic.sh $IP_CLIENTA_MGMT $IP_SERVERA_MGMT $IP_SERVERA 1234;
#    utils/static_traffic.sh $IP_CLIENTB_MGMT $IP_SERVERB_MGMT $IP_SERVERB 1234) &

#utils/static_traffic.sh $IP_CLIENTA_MGMT $IP_SERVERA_MGMT $IP_SERVERA 1234
#utils/static_traffic.sh $IP_CLIENTB_MGMT $IP_SERVERB_MGMT $IP_SERVERB 1234


read

echo "Stopping traffic"
stop_traffic

read

done

#./monitor.sh

#sleep 60
