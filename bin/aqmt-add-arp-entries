#!/bin/bash
#
# This script sets static arp routes on the testbed
# so that tests are not interrupted with arp requests.
#
# Run this from the aqm-machine.
#

set -ex
source aqmt-vars.sh

mac_clienta=$(ssh $IP_CLIENTA_MGMT "ip l show $IFACE_ON_CLIENTA | grep ether | awk '{ print \$2 }'")
mac_clientb=$(ssh $IP_CLIENTB_MGMT "ip l show $IFACE_ON_CLIENTB | grep ether | awk '{ print \$2 }'")
mac_servera=$(ssh $IP_SERVERA_MGMT "ip l show $IFACE_ON_SERVERA | grep ether | awk '{ print \$2 }'")
mac_serverb=$(ssh $IP_SERVERB_MGMT "ip l show $IFACE_ON_SERVERB | grep ether | awk '{ print \$2 }'")

mac_aqm_clients=$(ip l show $IFACE_CLIENTS | grep ether | awk '{ print $2 }')
mac_aqm_servera=$(ip l show $IFACE_SERVERA | grep ether | awk '{ print $2 }')
mac_aqm_serverb=$(ip l show $IFACE_SERVERB | grep ether | awk '{ print $2 }')

# clients -> aqm
ssh root@$IP_CLIENTA_MGMT "arp -i $IFACE_ON_CLIENTA -s $IP_AQM_C $mac_aqm_clients"
ssh root@$IP_CLIENTB_MGMT "arp -i $IFACE_ON_CLIENTB -s $IP_AQM_C $mac_aqm_clients"

# aqm -> clients
sudo arp -i $IFACE_CLIENTS -s $IP_CLIENTA $mac_clienta
sudo arp -i $IFACE_CLIENTS -s $IP_CLIENTB $mac_clientb

# servers -> aqm
ssh root@$IP_SERVERA_MGMT "arp -i $IFACE_ON_SERVERA -s $IP_AQM_SA $mac_aqm_servera"
ssh root@$IP_SERVERB_MGMT "arp -i $IFACE_ON_SERVERB -s $IP_AQM_SB $mac_aqm_serverb"

# aqm -> servers
sudo arp -i $IFACE_SERVERA -s $IP_SERVERA $mac_servera
sudo arp -i $IFACE_SERVERB -s $IP_SERVERB $mac_serverb
