#!/bin/bash

# this scripts controls static (greedy) traffic from a server to a client
# it will set up the server and connect with the client on the specified port

terminate=0

while getopts "k" opt; do
    case $opt in
        k) terminate=1 ;;
    esac
done

shift $((OPTIND-1))

if [ -z $3 ] || ([ -z $4 ] && [ $terminate -eq 0 ]); then
    echo "Usage: $0 [-k] <client mgmt ip> <server mgmt ip> <server ip> <port>"
    echo "        -k is used to kill the connection"
    echo "           (port is optional with -k)"
    exit 1
fi

ip_client_mgmt=$1
ip_server_mgmt=$2
ip_server=$3
port=$4

if [ $terminate -eq 1 ]; then
    if [ -z $port ]; then
        ssh $ip_client_mgmt "killall nc 2>/dev/null"
        ssh $ip_server_mgmt "killall nc 2>/dev/null"
    else
        ssh $ip_client_mgmt "pgrep -f \"nc -d $ip_server $port\" | xargs kill"
        ssh $ip_server_mgmt "pgrep -f \"nc -l $port\" | xargs kill"
    fi

    exit 0
fi

ssh $ip_server_mgmt "nohup cat /dev/zero | nc -l $port >/dev/null 2>&1 &"
ssh $ip_client_mgmt "nohup nc -d $ip_server $port >/dev/null 2>&1 </dev/null &"

exit 0
