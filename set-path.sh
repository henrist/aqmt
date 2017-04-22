#!/bin/bash
#
# Source this file to set up PATH and PYTHONPATH
# correctly without having to make symlinks.
#

if [[ $PATH == *"$(pwd)"* ]]; then
    echo "You have already added the path!"
    exit
fi

export PATH="$(pwd)/bin:$PATH"
export PYTHONPATH="$(pwd):$PYTHONPATH"
