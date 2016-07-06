#!/bin/bash
set -e

. "$(dirname $(readlink -f $BASH_SOURCE))/common.sh"

# interfaces:
#   enp2s0f1   To client A (10.0.1.211) and client B (10.0.1.210)
#   enp2s0f2   To server A (10.0.3.201)
#   enp2s0f3   To server B (10.0.2.200)


#ctrlrate=400mbit
testrate=40mbit

#aqm_name=dualq
#aqm_params="l_thresh_us 1000 offset 0 l_slope 5 c_slope 4 l_smooth 0 c_smooth 5 l_power 1 c_power 2 l_shift 50"

#server_rtt=200 # in ms


stop_traffic() {
    :
    utils/static_traffic.sh -k client-a server-a
    utils/static_traffic.sh -k client-b server-b
}


configure_clients_edge() {

    tc qdisc  add dev $clients_iface root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
    tc qdisc  add dev $clients_iface parent 1:2 handle 12: htb default 10
    tc class  add dev $clients_iface parent 12: classid 10 htb rate $testrate   #burst 1516
    tc filter add dev $clients_iface parent 1:0 protocol ip prio 1 u32 match ip src $clients_aqm_ip flowid 1:1

    # htb = hierarchy token bucket - used to limit bandwidth
    # default traffic to the class with minor-id 5




    #tc qdisc add dev $clients_iface root handle 1: htb default 5
    #tc class add dev $clients_iface parent 1: classid 1:5 htb rate $ctrlrate
    #tc class add dev $clients_iface parent 1: classid 1:10 htb rate $testrate burst 1516
    #tc filter add dev $clients_iface protocol ip parent 1:0 prio 1 u32 match ip src $servera_ip flowid 1:10
    #tc filter add dev $clients_iface protocol ip parent 1:0 prio 1 u32 match ip src $serverb_ip flowid 1:10

    # use the preferred aqm
    #tc qdisc add dev $clients_iface parent 12:10 $aqm_name $aqm_params

    #tc qdisc add dev $clients_iface parent 12:10 red limit 1000000 avpkt 1000 ecn #adaptive #bandwidth $testrate #10Mbit
}

configure_servers_edge() {
    # set up rtt on server edges
    for x in $servera_ip:$servera_iface:$servera_aqm_ip:40 \
             $serverb_ip:$serverb_iface:$serverb_aqm_ip:40; do
        server_ip=$(echo $x | cut -f1 -d:)
        server_iface=$(echo $x | cut -f2 -d:)
        server_aqm_ip=$(echo $x | cut -f3 -d:)
        server_rtt=$(echo $x | cut -f4 -d:)

        delay=$(echo "scale=2; $server_rtt / 2" | bc)  # delay is half the rtt

        # put traffic in band 1 by default
        # delay traffic in band 1
        # filter traffic from aqm node itself into band 0 for priority and no delay
        tc qdisc  add dev $server_iface root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
        tc qdisc  add dev $server_iface parent 1:2 handle 12: netem delay ${delay}ms # todo: put "limit" ?
        tc filter add dev $server_iface parent 1:0 protocol ip prio 1 u32 match ip src $server_aqm_ip flowid 1:1

        ssh $server_ip "
            sudo tc qdisc  add dev enp3s0 root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
            sudo tc qdisc  add dev enp3s0 parent 1:2 handle 12: netem delay ${delay}ms;
            sudo tc filter add dev enp3s0 parent 1:0 protocol ip prio 1 u32 match ip dst $server_aqm_ip flowid 1:1"
    done

}

#start_traffic_analyzer() {
    #sudo ./ta $iface "${pcapfilter}" ${mainfolder}1000${foldername} 1000 $ipclass 250 &
#}



trap stop_traffic EXIT

while true; do

utils/reset.sh

#utils/configure_host_cc.sh client-a dctcp 1
#utils/configure_host_cc.sh server-a dctcp 1
#utils/configure_host_cc.sh client-b dctcp 1
#utils/configure_host_cc.sh server-b dctcp 1

configure_clients_edge
configure_servers_edge

#(sleep 2;
#    utils/static_traffic.sh client-a server-a 1234;
#    utils/static_traffic.sh client-b server-b 1234) &

utils/static_traffic.sh client-a server-a 1234
#utils/static_traffic.sh client-b server-b 1234


read

stop_traffic

read

done

#./monitor.sh

#sleep 60
