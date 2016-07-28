#!/bin/bash

. "$(dirname $(readlink -f $BASH_SOURCE))/vars.sh"

# run all tc and ip commands through sudo if needed
function tc {
    if [ $(id -u) -ne 0 ]; then
        sudo $tc "$@"
    else
        command $tc "$@"
    fi
}

function ip {
    if [ $(id -u) -ne 0 ]; then
        sudo ip "$@"
    else
        command ip "$@"
    fi
}
