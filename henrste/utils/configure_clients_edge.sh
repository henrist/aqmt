#!/bin/bash

# this scripts configure the egress on clients and aqm
# and should be run on the aqm-machine

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

if [ $# -lt 3 ] || [ $# -eq 4 ] || [ $# -gt 5 ]; then
    >&2 echo "Usage: $0 <testrate> [<rtt> [<aqm_name> [<aqm_params>]]]"
    >&2 echo "Example: $0 10mbit 100 red"
    exit 1
fi

testrate=$1
rtt=$2 # in ms
aqm_name=$3
aqm_params=$4

#aqm_name=red
#aqm_params="limit 1000000 avpkt 1000 ecn" #adaptive #bandwidth $testrate #10Mbit

configure_clients_edge_aqm_node $testrate $rtt $aqm_name "$aqm_params"
configure_clients_node $rtt
