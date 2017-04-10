#!/bin/bash

#tc=/home/testbed/dual-queue-aqm/iproute2-3.16.0/tc/tc
tc=tc

# load variables if running on simula testbed
if [ "$(hostname)" == "ford" ]; then
    . "$(dirname $(readlink -f $BASH_SOURCE))/simula_testbed.env"
fi

if ! [[ "$PATH" = *iproute2-l4s* ]] && [ -f "$(dirname $(readlink -f $BASH_SOURCE))/../iproute2-l4s/tc/tc" ]; then
    export PATH="$(dirname $(readlink -f $BASH_SOURCE))/../iproute2-l4s/tc:$PATH"
fi

ADDITIONAL_VARS=""
if ip a show | grep -q "$IP_AQM_C/"; then
    # additional vars on the AQM
    ADDITIONAL_VARS="
             IFACE_ON_CLIENTA
             IFACE_ON_CLIENTB
             IFACE_ON_SERVERA
             IFACE_ON_SERVERB
             "
else
    # additional vars on client/servers
    ADDITIONAL_VARS="
             IFACE_AQM
             "
fi

error=0
for check in \
             $ADDITIONAL_VARS \
             IP_AQM_C \
             IP_AQM_MGMT \
             IP_AQM_SA \
             IP_AQM_SB \
             IP_CLIENTA \
             IP_CLIENTA_MGMT \
             IP_CLIENTB \
             IP_CLIENTB_MGMT \
             IP_SERVERA \
             IP_SERVERA_MGMT \
             IP_SERVERB \
             IP_SERVERB_MGMT \
             ; do
    if [ -z $(printenv "$check") ]; then
        echo "Missing environment variable $check"
        error=1
    fi
done

if [ $error -eq 1 ]; then
    return 1 2>/dev/null || exit 1
fi
