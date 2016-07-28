#!/bin/bash
set -e

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. common.sh

testrate=10mbit

rtt_clients=1000 # in ms
rtt_servera=1000 # in ms
rtt_serverb=1000 # in ms

aqm_name=
aqm_params=

#aqm_name=dualq
#aqm_params="l_thresh_us 1000 offset 0 l_slope 5 c_slope 4 l_smooth 0 c_smooth 5 l_power 1 c_power 2 l_shift 50"

stop_traffic() {
    :
    utils/static_traffic.sh -k $IP_CLIENTA_MGMT $IP_SERVERA_MGMT $IP_SERVERA 1234
    utils/static_traffic.sh -k $IP_CLIENTB_MGMT $IP_SERVERB_MGMT $IP_SERVERB 1234
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
