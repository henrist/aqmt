#!/bin/bash

# this script opens four tmux panes and generates greedy traffic
# from servera to clienta and
# from serverb to clientb

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

cmds=()
cmds+=("sleep 0.2; ssh -t $IP_CLIENTA_MGMT /opt/testbed/greedy_generator/greedy -vv $IP_SERVERA 1234; read")
cmds+=("ssh -t $IP_SERVERA_MGMT /opt/testbed/greedy_generator/greedy -vv -s 1234; read")
#cmds+=("sleep 0.2; ssh -t $IP_CLIENTB_MGMT /opt/testbed/greedy_generator/greedy -vv $IP_SERVERB 1234; read")
#cmds+=("ssh -t $IP_SERVERB_MGMT /opt/testbed/greedy_generator/greedy -vv -s 1234; read")
#cmds+=("sleep 0.2; ssh -t $IP_CLIENTB_MGMT /opt/testbed/greedy_generator/greedy -vv $IP_SERVERB 1235; read")
#cmds+=("ssh -t $IP_SERVERB_MGMT /opt/testbed/greedy_generator/greedy -vv -s 1235; read")

sn="greedy-$(date +%s)"
for i in ${!cmds[@]}; do
    cmd="${cmds[$i]}"

    if [ $i -eq 0 ]; then
        if [ -z $TMUX ]; then
            tmux new-session -d -n $sn "$cmd"
        else
            tmux new-window -n $sn "$cmd"
        fi
    else
        tmux split-window -t $sn "$cmd"
    fi

    tmux select-layout -t $sn tiled
done

tmux select-layout -t $sn tiled
tmux set-window -t $sn synchronize-panes

if [ -z $TMUX ]; then
    tmux attach-session
fi
