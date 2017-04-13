#!/bin/bash

# this script reports the delta of number of (non-dropped) packets on the
# interfaces as well as number of dropped packets
#
# run it on the relevant machines to watch status

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../vars.sh

sleeptime=1

get_num() {
    echo "$1" | grep "$2" | sed "s/.*$3://" | sed 's/ .*//'
}

if ! [[ $(ip addr show to $IP_AQM_C) ]]; then
    # reporting from client/server
    last=(0 0 0 0)

    while true; do
        new=()

        stats=$(ifconfig $IFACE_AQM | grep dropped)
        new+=($(get_num "$stats" RX packets))
        new+=($(get_num "$stats" RX dropped))
        new+=($(get_num "$stats" TX packets))
        new+=($(get_num "$stats" TX dropped))

        printf "$(date +%M%S) $(hostname)    RX %-8d / %-8d   TX %-8d / %d\n" \
            "$((${new[0]}-${last[0]}))" \
            "$((${new[1]}-${last[1]}))" \
            "$((${new[2]}-${last[2]}))" \
            "$((${new[3]}-${last[3]}))"

        for i in ${!last[@]}; do
            last[$i]=${new[$i]}
        done
        sleep $sleeptime
    done
else
    # reporting from AQM
    last=(0 0 0 0 0 0 0 0)

    while true; do
        echo
        new=()

        stats=$(ifconfig $IFACE_CLIENTS | grep dropped)
        new+=($(get_num "$stats" RX packets))
        new+=($(get_num "$stats" RX dropped))
        new+=($(get_num "$stats" TX packets))
        new+=($(get_num "$stats" TX dropped))

        stats=$(ifconfig $IFACE_SERVERA | grep dropped)
        new+=($(get_num "$stats" RX packets))
        new+=($(get_num "$stats" RX dropped))
        new+=($(get_num "$stats" TX packets))
        new+=($(get_num "$stats" TX dropped))

        printf "$(date +%M%S) to clients  RX %-8d / %-8d   TX %-8d / %d\n" \
            "$((${new[0]}-${last[0]}))" \
            "$((${new[1]}-${last[1]}))" \
            "$((${new[2]}-${last[2]}))" \
            "$((${new[3]}-${last[3]}))"

        printf "$(date +%M%S) to server   RX %-8d / %-8d   TX %-8d / %d\n" \
            "$((${new[4]}-${last[4]}))" \
            "$((${new[5]}-${last[5]}))" \
            "$((${new[6]}-${last[6]}))" \
            "$((${new[7]}-${last[7]}))"

        for i in ${!last[@]}; do
            last[$i]=${new[$i]}
        done

        sleep $sleeptime
    done
fi
