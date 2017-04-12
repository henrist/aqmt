#!/bin/bash

# This script reads relevant values from the different machines
# and can be used to verify the configuration.
#
# Run from the AQM machine.

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

require_on_aqm_node

# -- get from localhost (aqm)

names=(clients servera serverb)
ifaces=($IFACE_CLIENTS $IFACE_SERVERA $IFACE_SERVERB)
for i in ${!ifaces[@]}; do
    echo
    echo "---- ${names[$i]} --] aqm ----"
    ethres=$(sudo ethtool -k ${ifaces[$i]})
    echo "$ethres" | grep generic-segmentation-offload
    echo "$ethres" | grep tcp-segmentation-offload
    echo "txqueuelen: $(ip l show ${ifaces[$i]} | grep qlen | sed 's/.*qlen\s\+\([0-9]\+\).*/\1/')"

done

# -- get from remote nodes

names=(clienta clientb servera serverb)
hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT)
ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB $IFACE_ON_SERVERA $IFACE_ON_SERVERB)

for i in ${!ifaces[@]}; do
    ssh root@${hosts[$i]} "
        echo
        echo '---- ${names[$i]} [-- aqm ----'
        ethres=\$(sudo ethtool -k ${ifaces[$i]})
        echo \"\$ethres\" | grep generic-segmentation-offload
        echo \"\$ethres\" | grep tcp-segmentation-offload
        echo \"txqueuelen: \$(ip l show ${ifaces[$i]} | grep qlen | sed 's/.*qlen\s\+\([0-9]\+\).*/\1/')\"
        "
done
