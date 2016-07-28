#!/bin/bash

docker-compose up -d

docker-compose exec aqm printenv

#    tc qdisc  add dev $servers_iface root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
#    tc qdisc  add dev $servers_iface parent 1:2 handle 12: netem delay 50ms # todo: put "limit" ?
#    tc filter add dev $servers_iface parent 1:0 protocol ip prio 1 u32 match ip src 10.25.2.2 flowid 1:1
