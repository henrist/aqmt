#!/bin/bash

ifnum=$(docker-compose exec aqm ip a show to 10.25.1.0/24 \
        | head -1 | awk -F: '{print $1}')

iface=$(ip l | grep "@if$ifnum" | sed 's/.*: \(veth.*\)@.*/\1/')

echo "$iface"
