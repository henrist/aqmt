#!/bin/bash

# Usage: ./greedy.sh servera
#        ./greedy.sh clienta 10.25.2.21

if [ -n "$2" ]; then
    sleep 0.2
    ../ssh.sh $1 greedy -b 2000000 -vv -t 1000 $2 1234
else
    ../ssh.sh $1 greedy -r -s -b 10000000000 -vv -t 1000 1234
fi
