#!/bin/bash

# this script generates udp traffic

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

tos=""
tos="--tos 0x01" # ECT(1)

cmds=()
#cmds+=("ssh -t $IP_SERVERA_MGMT nping --udp $tos -g 1234 -p 1234 -c 0 $IP_CLIENTA --data-length 1472 --delay 0.001 --quiet; read")
#cmds+=("ssh -t $IP_SERVERA_MGMT nping --udp $tos -g 1234 -p 1234 -c 0 $IP_CLIENTA --data-length 1472 --delay 0.003 --quiet; read")
#cmds+=("ssh -t $IP_SERVERB_MGMT nping --udp $tos -g 1234 -p 1234 -c 0 $IP_CLIENTB --data-length 1472 --delay 0.001 --quiet; read")
#cmds+=("ssh -t $IP_SERVERB_MGMT nping --udp $tos -g 1234 -p 1234 -c 0 $IP_CLIENTB --data-length 1472 --delay 0.005 --quiet; read")

# iperf3 currently only sends packets every 100 ms which causes bursts (fix is not upstream yet)
# iperf2 does not have this problem, but packets are still not paced perfectly

cmds+=("ssh -t $IP_CLIENTA_MGMT iperf -s; read")
cmds+=("sleep 0.2; ssh -t $IP_SERVERA_MGMT iperf -c $IP_CLIENTA $tos -u -l 1458 -R -b $((10*1000*1000)) -i 1 -t 99999; read")

sn="udp-$(date +%s)"
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
