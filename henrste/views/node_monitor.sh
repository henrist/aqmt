#!/bin/bash
# run this on the different clients/servers
# it will monitor various parameters for you

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

require_not_on_aqm_node

if [ -z $TMUX ]; then
    tmux new-session "./node_monitor.sh"
    exit 0
fi

cmds=()
cmds[0]="watch -n .2 ./show_setup.sh -vi \$IFACE_AQM"
cmds[1]="./monitor_iface_status.sh"

sn="node-monitor-$(date +%s)"

i=0
for cmd in "${cmds[@]}"; do
    i=$(($i+1))
    if [ $i -eq 1 ]; then
        tmux new-window -n $sn $cmd
    else
        tmux split-window -t $sn $cmd
        tmux select-layout -t $sn even-vertical
    fi
done

tmux select-layout -t $sn even-vertical
tmux set-window -t $sn synchronize-panes
