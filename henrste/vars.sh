#!/bin/bash

#tc=/home/testbed/dual-queue-aqm/iproute2-3.16.0/tc/tc
tc=tc

# load variables if running on simula testbed
if [ "$(hostname)" == "ford" ]; then
    . "$(dirname $(readlink -f $BASH_SOURCE))/load-env-simula-testbed.sh"
fi

error=0
for check in IFACE_CLIENTS \
             IFACE_SERVERA \
             IFACE_SERVERB \
             IP_AQM_MGMT \
             IP_AQM_C \
             IP_AQM_SA \
             IP_AQM_SB \
             IP_CLIENTA_MGMT \
             IP_CLIENTA \
             IP_CLIENTB_MGMT \
             IP_CLIENTB \
             IP_SERVERA_MGMT \
             IP_SERVERA \
             IP_SERVERB_MGMT \
             IP_SERVERB; do
    if [ -z $(printenv "$check") ]; then
        echo "Missing environment variable $check"
        error=1
    fi
done

if [ $error -eq 1 ]; then
    exit 1
fi

if [ -z $IFACE_ON_SERVERA ]; then
    IFACE_ON_SERVERA=enp3s0
fi

if [ -z $IFACE_ON_SERVERB ]; then
    IFACE_ON_SERVERB=enp3s0
fi
