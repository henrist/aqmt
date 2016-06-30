#!/bin/bash

# this script shows the current tc/ip setup on the local computer
# (it is piped through less to make it easier to use)

. common.sh

links=$(ip link show up | grep -v "^ " | sed 's/.*: \([^:]\+\):.*/\1/')
tc_verbose=

while getopts "v" opt; do
    case $opt in
        v)
            tc_verbose=-s
    esac
done
shift $((OPTIND-1))

if ! [ -z "$@" ]; then
    links="$@"
fi

function echo_indent {
    echo "$@" | sed 's/^/  /'
}

function show {
    echo "#### Showing network setup ####"
    echo "Syntax: ./show_setup.sh [-v] [interface1] [interface2] [...]"

    for link in $links; do
        echo
        echo
        echo "------------ link: $link ------------"

        echo
        echo "qdisc:"
        echo_indent "$(tc $tc_verbose qdisc show dev $link)"
        
        out=$(tc $tc_verbose class show dev $link)
        if ! [ -z "$out" ]; then
            echo
            echo "class:"
            echo_indent "$out"
        fi

        out=$(tc filter show dev $link)
        if ! [ -z "$out" ]; then
            echo
            echo "filter:"
            echo_indent "$out"
        fi

        #echo
        #echo "ip:"
        #echo_indent "$(ip addr show dev $link)"
    done
}

show | less -c