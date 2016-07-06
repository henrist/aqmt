#!/bin/bash

# this scripts controls static (greedy) traffic from a server to a client
# it will set up the server and connect with the client on the specified port

terminate=0

while getopts "k" opt; do
    case $opt in
        k)
            terminate=1
            ;;
    esac
done

shift $((OPTIND-1))

if [ -z $2 ] || ([ -z $3 ] && [ $terminate -eq 0 ]); then
    echo "Syntax: $0 [-k] <client> <server> <port>"
    echo "        -k is used to kill the connection"
    echo "           (port is optional with -k)"
    exit 1
fi

client=$1
server=$2
port=$3

if [ $terminate -eq 1 ]; then
    if [ -z $3 ]; then
        ssh $client "killall nc 2>/dev/null"
        ssh $server "killall nc 2>/dev/null"
    else
        ssh $client "pgrep -f \"nc -d $server $port\" | xargs kill"
        ssh $server "pgrep -f \"nc -l $port\" | xargs kill"
    fi

    exit 0
fi

ssh $server "nohup cat /dev/zero | nc -l $port >/dev/null 2>&1 &"
ssh $client "nohup nc -d $server $port >/dev/null 2>&1 </dev/null &"

exit 0
