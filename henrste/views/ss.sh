#!/bin/bash
# run this on aqm

check() {
    title=$1
    host=$2
    ret=$(ssh $host "
        ss -nei --memory '( ( sport >= :5500 and sport <= :5600 ) or ( dport >= :5500 and dport <= :5600 ) )' | tail -n+2
        ")

    if [ -n "$ret" ]; then
        # https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
        col1=$(printf '\033[45m\033[37m')
        col2=$(printf '\033[46m\033[37m')
        col3=$(printf '\033[42m\033[30m')
        normal=$(echo -e '\033[0m')

        echo
        echo "---- $title ----"
        echo
        echo "$ret" | sed 's/^/  /' | sed 's/ segs_out/\n         segs_out/' \
            | sed "s/\(unacked:[0-9]\+\)/${col1}\1${normal}/" \
            | sed "s/\(cwnd:[0-9]\+\)/${col2}\1${normal}/" \
            | sed "s/\(tb[0-9]\+\)/${col3}\1${normal}/" \
            | sed "s/\(rb[0-9]\+\)/${col3}\1${normal}/"
    fi
}

check clienta $IP_CLIENTA_MGMT
check servera $IP_SERVERA_MGMT
check clientb $IP_CLIENTB_MGMT
check serverb $IP_SERVERB_MGMT
