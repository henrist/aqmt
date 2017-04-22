#!/bin/bash

# this script shows the current tc/ip setup on the local computer
# (it is piped through less to make it easier to use)

set -e
source aqmt-vars.sh

links=$(ip link show up | grep -v "^ " | sed 's/.*: \([^:@]\+\)[:@].*/\1/')
verbose=
show_ip=0
show_link=0
show_route=0
show_filter=0

while getopts "fhilrv" opt; do
    case $opt in
        h)
            echo "Usage: ./show_setup.sh [-hilrv] [interface ...]"
            echo "  -h  show help"
            echo "  -f  show ip filter details"
            echo "  -i  show ip addr details"
            echo "  -l  show ip link details"
            echo "  -r  show ip route details"
            echo "  -v  show statistics"
            exit
            ;;
        f) show_filter=1 ;;
        i) show_ip=1 ;;
        l) show_link=1 ;;
        r) show_route=1 ;;
        v) verbose="-s -d" ;;
    esac
done
shift $((OPTIND-1))

if [ $# -gt 0 ]; then
    links="$@"
fi

echo_indent() {
    echo "$@" | sed 's/^/  /'
}

show() {
    first=1
    for link in $links; do
        if [ $first -eq 0 ]; then
            echo
        fi
        first=0

        ip=$(ip addr show dev $link | grep "inet " | sed 's/.*inet \? \(.*\)\/.*/\1/')
        echo "------------ link: $link (${ip//$'\n'/, }) ------------"

        echo "qdisc:"
        echo_indent "$(tc $verbose qdisc show dev $link)"

        out=$(tc $verbose class show dev $link)
        if ! [ -z "$out" ]; then
            echo "class:"
            echo_indent "$out"
        fi

        if [ $show_filter -eq 1 ]; then
            out=$(tc filter show dev $link)
            if ! [ -z "$out" ]; then
                echo "filter:"
                echo_indent "$out"
            fi
        fi

        if [ $show_ip -eq 1 ]; then
            echo "ip:"
            echo_indent "$(ip $verbose addr show dev $link)"
        fi

        if [ $show_link -eq 1 ]; then
            echo "link:"
            echo_indent "$(ip $verbose link show dev $link)"
        fi

        if [ $show_route -eq 1 ]; then
            echo "route:"
            echo_indent "$(ip $verbose route show dev $link)"
        fi
    done
}

show | less -c
