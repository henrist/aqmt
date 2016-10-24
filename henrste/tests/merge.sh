#!/bin/bash

if [ -z $2 ]; then
    echo "Missing setfolder argument and/or testfolders"
    exit 1
fi

collection=$1

for file in "qs_ecn_stats" "qs_nonecn_stats" "util_stats" "d_percent_ecn_stats" "d_percent_nonecn_stats" "m_percent_ecn_stats"; do
    out="$collection/$file"
    truncate -s0 $out
    head -1 "$collection/${3##*/}/$file" >$out
    for x in ${@:2}; do
        x="${x##*/}"
        tag=$(($(grep ^x_udp_rate "$collection/$x/details" | awk '{ print $2 }')/1000))
        #tag="unknown"
        tail -n+2 "$collection/$x/$file" | sed "s/^/$tag /" >>$out
    done
done
