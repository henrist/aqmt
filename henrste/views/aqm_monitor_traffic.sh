#!/bin/bash

# run this on the aqm-machine

# this script opens three panes and monitor the three interfaces
# showing their current bandwidth

# example:
# ./aqm_monitor_traffic.sh 0.05 <number-mbit>

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

delay=0.05
max=$((1000*1000*12/8))

ifaces=($IFACE_CLIENTS $IFACE_SERVERA $IFACE_SERVERB)

if [ ${#ifaces[@]} -eq 0 ]; then
    echo "Missing IFACE_* environment variables"
    exit 1
fi

if [ -z $TMUX ]; then
    echo "Run this inside tmux!"
    exit 1
fi

if ! [ -z $1 ]; then
    delay=$1
fi

if ! [ -z $2 ]; then
    max=$((1024*1024*$2/8))
fi

sn="monitor-$(date +%s)"

i=0
for iface in ${ifaces[@]}; do
    cmd="speedometer -s -i $delay -l -r $iface -t $iface -m $max"

    i=$(($i+1))
    if [ $i -eq 1 ]; then
        tmux new-window -n $sn $cmd
    else
        tmux split-window -t $sn $cmd
        tmux select-layout -t $sn even-horizontal
    fi
done

tmux select-layout -t $sn even-horizontal
tmux set-window -t $sn synchronize-panes
