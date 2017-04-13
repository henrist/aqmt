#!/bin/bash

# run this on the aqm-machine

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

require_on_aqm_node

if [ -z $TMUX ]; then
    echo "Run this inside tmux!"
    exit 1
fi

cmds=()
cmds[0]="watch -n .2 ./show_setup.sh -vir $IFACE_CLIENTS"
#cmds[1]="watch -n .2 ./show_setup.sh -vir $IFACE_SERVERA"

sn="setup-$(date +%s)"

i=0
for cmd in "${cmds[@]}"; do
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
