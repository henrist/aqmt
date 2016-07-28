#!/bin/bash

# this scripts resets all nodes and edges to base configuration

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

reset_aqm_client_edge
reset_aqm_server_edge
reset_all_hosts_edge
reset_all_hosts_cc
