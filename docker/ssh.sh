#!/bin/bash

if [ -z $1 ]; then
    echo "Please specify a container to connect to"
    exit 1
fi

map=(
  "aqm 10.25.0.2"
  "clienta 10.25.0.11"
  "clientb 10.25.0.12"
  "servera 10.25.0.21"
  "serverb 10.25.0.31"
)

host=""
for row in "${map[@]}"; do
    if [ "$(echo "$row" | cut -f1 -d" ")" == "$1" ]; then
        host=$(echo "$row" | cut -f2 -d" ")
        break
    fi
done

if [ -z "$host" ]; then
    echo "Unknown host $1"
    exit 1
fi

cmd=""
if [ "$#" -gt 1 ]; then
    cmd="${@:2}"
fi

ssh -t -i container/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$host "$cmd"
