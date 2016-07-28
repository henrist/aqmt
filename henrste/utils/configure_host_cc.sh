#!/bin/bash

# this scripts sets congestion control on a host

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

if [ -z $3 ]; then
    echo "Usage: $0 <host> <tcp_congestion_control> <tcp_ecn>"
    exit 1
fi

host=$1
tcp_congestion_control=$2
tcp_ecn=$3

set_host_cc $host $tcp_congestion_control $tcp_ecn
