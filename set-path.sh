#!/bin/bash
#
# Source this file to set up PATH and PYTHONPATH
# correctly without having to make symlinks.
#

p="$(dirname $(readlink -f $BASH_SOURCE))"

if [[ $PATH == *"$p"* ]]; then
    echo "You have already added the path!"
    return 1
fi

export PATH="$p/bin:$PATH"
export PYTHONPATH="$p:$PYTHONPATH"
