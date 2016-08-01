#!/bin/bash

# run this on the aqm-machine

cd "$(dirname $(readlink -f $BASH_SOURCE))"

cmds=()
cmds[0]="watch -n .2 ../show_setup.sh -vir $IFACE_CLIENTS"
cmds[1]="watch -n .2 ../show_setup.sh -vir $IFACE_SERVERA"

tmux split-window -v ${cmds[1]}
${cmds[0]}
