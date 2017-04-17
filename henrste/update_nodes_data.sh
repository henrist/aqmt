#!/bin/bash

# This scripts upload needed scripts and programs
# to the clients and servers

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. vars.sh

set -e

if ! [ -f ../greedy_generator/greedy ]; then
    echo "You have to build the utils before you can run this script"
    echo "(Missing binary of greedy_generator)"
    exit 1
fi

if [ -f /testbed-is-docker ]; then
    echo "You can't run this inside Docker - and there is no need to!"
    exit 1
fi

f=/opt/testbed/henrste/vars.sh

for ip in $IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT; do
    ssh root@$ip '
        mkdir -p /opt/testbed/greedy_generator
        mkdir -p /opt/testbed/henrste/utils
        rm -Rf /opt/testbed/henrste/views
        mkdir -p /opt/testbed/henrste/views

        echo "export IP_AQM_MGMT='$IP_AQM_MGMT'" >'$f'
        echo "export IP_AQM_C='$IP_AQM_C'" >>'$f'
        echo "export IP_AQM_SA='$IP_AQM_SA'" >>'$f'
        echo "export IP_AQM_SB='$IP_AQM_SB'" >>'$f'
        echo "export IP_CLIENTA_MGMT='$IP_CLIENTA_MGMT'" >>'$f'
        echo "export IP_CLIENTA='$IP_CLIENTA'" >>'$f'
        echo "export IP_CLIENTB_MGMT='$IP_CLIENTB_MGMT'" >>'$f'
        echo "export IP_CLIENTB='$IP_CLIENTB'" >>'$f'
        echo "export IP_SERVERA_MGMT='$IP_SERVERA_MGMT'" >>'$f'
        echo "export IP_SERVERA='$IP_SERVERA'" >>'$f'
        echo "export IP_SERVERB_MGMT='$IP_SERVERB_MGMT'" >>'$f'
        echo "export IP_SERVERB='$IP_SERVERB'" >>'$f
    scp -p ../greedy_generator/greedy root@$ip:/opt/testbed/greedy_generator/greedy
    scp -p utils/set_sysctl_tcp_mem.sh root@$ip:/opt/testbed/henrste/utils/
    scp -p views/* root@$ip:/opt/testbed/henrste/views/
    scp -rp ../tcp_dctcp root@$ip:/opt/testbed/tcp_dctcp

    ssh root@$ip '
        cd /opt/testbed/tcp_dctcp
        make
        make unload || :
        make load
        '
done

ssh root@$IP_CLIENTA_MGMT 'echo "export IFACE_AQM='$IFACE_ON_CLIENTA'" >>'$f
ssh root@$IP_CLIENTB_MGMT 'echo "export IFACE_AQM='$IFACE_ON_CLIENTB'" >>'$f
ssh root@$IP_SERVERA_MGMT 'echo "export IFACE_AQM='$IFACE_ON_SERVERA'" >>'$f
ssh root@$IP_SERVERB_MGMT 'echo "export IFACE_AQM='$IFACE_ON_SERVERB'" >>'$f
