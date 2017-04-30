#!/bin/bash

# Path to iproute2's tc command - can be overriden in environment file
# By default we use the one we find in PATH
tc=tc

# User provided environment should be placed in /etc/aqmt.env
# See aqmt.env.template for example.
if [ -f /etc/aqmt.env ]; then
    source /etc/aqmt.env
fi

# add our bin folder to PATH if needed
if ! [[ "$PATH" == *"aqmt"* ]]; then
    PATH="$(dirname $(readlink -f $BASH_SOURCE)):$PATH"
fi

# add python library to PYTHONPATH if needed
if ! [[ "$PYTONPATH" == *"aqmt"* ]]; then
    export PYTHONPATH="$(dirname $(readlink -f $BASH_SOURCE)):$PYTHONPATH"
fi
