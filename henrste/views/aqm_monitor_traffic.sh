#!/bin/bash

# run this on the aqm-machine

# this script opens three panes and monitor the three interfaces
# showing their current bandwidth

# example:
# ./aqm_monitor_traffic.sh 0.05 $((1024*1024*5))

delay=0.05
max=$((1024*1024*2))

ifaces=($IFACE_CLIENTS $IFACE_SERVERA $IFACE_SERVERB)

if [ ${#ifaces[@]} -eq 0 ]; then
    echo "Missing IFACE_* environment variables"
    exit 1
fi

if ! [ -z $1 ]; then
    delay=$1
fi

if ! [ -z $2 ]; then
    max=$2
fi

sn="monitor-$(date +%s)"

i=0
for iface in ${ifaces[@]}; do
    cmd="speedometer -i $delay -l -r $iface -t $iface -m $max"

    i=$(($i+1))
    if [ $i -eq 1 ]; then
        if [ -z $TMUX ]; then
            tmux new-session -d -n $sn $cmd
        else
            tmux new-window -n $sn $cmd
        fi
    else
        tmux split-window -t $sn $cmd
        tmux select-layout -t $sn even-horizontal
    fi
done

tmux select-layout -t $sn even-horizontal
tmux set-window -t $sn synchronize-panes

if [ -z $TMUX ]; then
    tmux attach-session
fi
