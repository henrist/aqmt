#!/bin/bash

set -e
source aqmt-vars.sh

if [ -n "$IFACE_AQM" ]; then
    echo "This script must be run on the AQM machine"
    exit 1
fi

if [ -z "$1" ]; then
    echo "Syntax: ./aqm_monitor_node.sh <node>"
    echo "Example: ./aqm_monitor_node.sh clienta"
    exit 1
fi

host=""
if [ "$1" = "clienta" ]; then
    host=$IP_CLIENTA_MGMT
elif [ "$1" = "clientb" ]; then
    host=$IP_CLIENTB_MGMT
elif [ "$1" = "servera" ]; then
    host=$IP_SERVERA_MGMT
elif [ "$1" = "serverb" ]; then
    host=$IP_SERVERB_MGMT
else
    echo "Unknown node"
    exit 1
fi

ssh -t $host bash -ic /opt/aqmt/henrste/views/node_monitor.sh
