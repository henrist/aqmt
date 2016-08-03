#!/bin/bash

set -e

# this scripts configures the network for a manual test

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

# reset everything just in case
./reset.sh

testrate=10mbit

rtt_clients=0 # in ms
rtt_servera=500 # in ms
rtt_serverb=1000 # in ms

aqm_name=
aqm_params=

#aqm_name=red
#aqm_params="limit 1000000 avpkt 1000 ecn adaptive bandwidth $testrate"

#aqm_name=dualq
#aqm_params="l_thresh_us 1000 offset 0 l_slope 5 c_slope 4 l_smooth 0 c_smooth 5 l_power 1 c_power 2 l_shift 50"

configure_clients_edge $testrate $rtt_clients $aqm_name "$aqm_params"


cc=dctcp
if [ $cc == "reno" ]; then
    configure_host_cc $IP_CLIENTA_MGMT reno 2
    configure_host_cc $IP_SERVERA_MGMT reno 2
    configure_host_cc $IP_CLIENTB_MGMT reno 2
    configure_host_cc $IP_SERVERB_MGMT reno 2
elif [ $cc == "dctcp" ]; then
    configure_host_cc $IP_CLIENTA_MGMT dctcp 1
    configure_host_cc $IP_SERVERA_MGMT dctcp 1
    configure_host_cc $IP_CLIENTB_MGMT dctcp 1
    configure_host_cc $IP_SERVERB_MGMT dctcp 1
elif [ $cc == "cubic" ]; then
    :
    # no need to do anything, it is the default after reset
fi


configure_server_edge $IP_SERVERA_MGMT $IP_AQM_SA $IFACE_SERVERA $IFACE_ON_SERVERA $rtt_servera
configure_server_edge $IP_SERVERB_MGMT $IP_AQM_SB $IFACE_SERVERB $IFACE_ON_SERVERB $rtt_serverb

clear
echo "Configured testbed:"
echo "  rate: $testrate (applied from router to clients)"
echo "  rtt to router:"
echo "    - clients: $rtt_clients ms"
echo "    - servera: $rtt_servera ms"
echo "    - serverb: $rtt_serverb ms"

if [ -n "$aqm_name" ]; then
    params=""
    if [ -n "$aqm_params" ]; then params=" ($aqm_params)"; fi
    echo "  aqm: $aqm_name$params"
else
    echo "  no aqm"
fi

for node in CLIENTA CLIENTB SERVERA SERVERB; do
    ip=IP_${node}_MGMT
    echo -n "  ${node,,}: "
    echo $(get_host_cc ${!ip} | tr '\n' ' ')
done
