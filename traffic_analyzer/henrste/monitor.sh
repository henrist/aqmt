#!/bin/bash

# this script opens three panes and monitor the three interfaces
# showing their current bandwidth

delay=1

if ! [ -z $1 ]; then
    delay=$1
fi

for x in 2 3 1; do
    cmd="speedometer -i $delay -l -r enp2s0f$x -t enp2s0f$x -m $((1024*1024*6))"

    if [ $x = 1 ]; then
        $cmd
    else
        tmux split-window $cmd
        tmux select-layout even-horizontal
    fi
done

