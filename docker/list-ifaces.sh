#!/bin/bash
#
# This file lists the interfaces on the docker host that the containers
# are using. This is usefull if you want to monitor the traffic through
# e.g. wireshark
#

show_iface() {
    name=$1
    cidr=$2
    comment=$3

    ifnum=$(docker-compose exec $name ip a show to $cidr \
          | head -1 | awk -F: '{print $1}')

    iface=$(ip l | grep "@if$ifnum" | sed 's/.*: \(veth.*\)@.*/\1/')

    echo "$name: $iface ($comment)"
}

show_iface aqm 10.25.1.0/24 "to clients"
show_iface aqm 10.25.2.0/24 "to server a"
show_iface aqm 10.25.3.0/24 "to server b"
echo
show_iface clienta 10.25.1.0/24 "to aqm"
show_iface clientb 10.25.1.0/24 "to aqm"
echo
show_iface servera 10.25.2.0/24 "to aqm"
show_iface serverb 10.25.3.0/24 "to aqm"
