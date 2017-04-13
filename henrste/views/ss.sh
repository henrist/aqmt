#!/bin/bash
# run this on aqm

check() {
    title=$1
    host=$2
    remote1=$3
    remote2=$4
    ret=$(ssh $host "
        ss -nei --memory '( src $remote1 or dst $remote1 or src $remote2 or dst $remote2 )' | tail -n+2
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

# a client can talk with two servers
# a server can talk with two clients
check clienta $IP_CLIENTA_MGMT $IP_SERVERA $IP_SERVERB
check servera $IP_SERVERA_MGMT $IP_CLIENTA $IP_CLIENTB
check clientb $IP_CLIENTB_MGMT $IP_SERVERA $IP_SERVERB
check serverb $IP_SERVERB_MGMT $IP_CLIENTA $IP_CLIENTB
