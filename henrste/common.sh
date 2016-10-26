#!/bin/bash

. "$(dirname $(readlink -f $BASH_SOURCE))/vars.sh"

# run all tc and ip commands through sudo if needed
tc() {
    if [ $(id -u) -ne 0 ]; then
        sudo $tc "$@"
    else
        command $tc "$@"
    fi
}

ip() {
    if [ $(id -u) -ne 0 ]; then
        sudo ip "$@"
    else
        command ip "$@"
    fi
}

configure_host_cc() {
    local host=$1
    local tcp_congestion_control=$2
    local tcp_ecn=$3

    local feature_ecn=""
    if [ "$tcp_ecn" == "1" ]; then
        feature_ecn=" features ecn"
    fi

    # the 10.25. range belongs to the Docker setup
    # it needs to use congctl for a per route configuration
    # (congctl added in iproute2 v4.0.0)
    ssh root@$host '
        if [ -f /proc/sys/net/ipv4/tcp_congestion_control ]; then
            sysctl -q -w net.ipv4.tcp_congestion_control='$tcp_congestion_control'
        else
            # we are on docker
            . /tmp/testbed-vars-local.sh
            if ip a show $IFACE_AQM | grep -q 10.25.1.; then
                # on client
                ip route replace 10.25.2.0/24 via 10.25.1.2 dev $IFACE_AQM congctl '$tcp_congestion_control$feature_ecn'
                ip route replace 10.25.3.0/24 via 10.25.1.2 dev $IFACE_AQM congctl '$tcp_congestion_control$feature_ecn'
            else
                # on server
                ip_prefix=$(ip a show $IFACE_AQM | grep "inet 10" | awk "{print \$2}" | sed "s/\.[0-9]\+\/.*//")
                ip route replace 10.25.1.0/24 via ${ip_prefix}.2 dev $IFACE_AQM congctl '$tcp_congestion_control$feature_ecn'
            fi
        fi
        sysctl -q -w net.ipv4.tcp_ecn='$tcp_ecn
}

configure_clients_edge_aqm_node() {
    local testrate=$1
    local rtt=$2
    local aqm_name=$3
    local aqm_params=$4

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # htb = hierarchy token bucket - used to limit bandwidth
    # netem = used to simulate delay (link distance)

    if [ $rtt -gt 0 ]; then
        if tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc netem 2:"; then
            tc qdisc change dev $IFACE_CLIENTS handle 2: htb delay ${delay}ms
            tc class change dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate
        else
            tc qdisc  del dev $IFACE_CLIENTS root 2>/dev/null || true
            tc qdisc  add dev $IFACE_CLIENTS root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
            tc filter add dev $IFACE_CLIENTS parent 1:0 protocol ip prio 1 u32 match ip src $IP_AQM_C flowid 1:1
            tc qdisc  add dev $IFACE_CLIENTS parent 1:2 handle 2:  netem delay ${delay}ms
            tc qdisc  add dev $IFACE_CLIENTS parent 2: handle 3: htb default 10
            tc class  add dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate   #burst 1516
        fi
    else
        if ! tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc netem 2:" && \
                tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc htb 3:"; then
            tc class change dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate
        else
            tc qdisc  del dev $IFACE_CLIENTS root 2>/dev/null || true
            tc qdisc  add dev $IFACE_CLIENTS root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
            tc filter add dev $IFACE_CLIENTS parent 1:0 protocol ip prio 1 u32 match ip src $IP_AQM_C flowid 1:1
            tc qdisc  add dev $IFACE_CLIENTS parent 1:2 handle 3: htb default 10
            tc class  add dev $IFACE_CLIENTS parent 3: classid 10 htb rate $testrate   #burst 1516
        fi
    fi

    if [ -n "$aqm_name" ]; then
        # update params if possible
        if tc qdisc show dev $IFACE_CLIENTS | grep -q "qdisc $aqm_name 15:"; then
            tc qdisc change dev $IFACE_CLIENTS handle 15: $aqm_name $aqm_params
            echo "Updated params on existing aqm"
        else
            tc qdisc  add dev $IFACE_CLIENTS parent 3:10 handle 15: $aqm_name $aqm_params
        fi
    fi
}

configure_clients_node() {
    local rtt=$1

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # netem = used to simulate delay (link distance)

    if [ $rtt -gt 0 ]; then
        hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT)
        ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB)
        for i in ${!hosts[@]}; do
            ssh root@${hosts[$i]} "
                # if possible update the delay rather than destroying the existing qdisc
                if tc qdisc show dev ${ifaces[$i]} | grep -q 'qdisc netem 12:'; then
                    tc qdisc change dev ${ifaces[$i]} handle 12: netem delay ${delay}ms
                else
                    tc qdisc  del dev ${ifaces[$i]} root 2>/dev/null || true
                    tc qdisc  add dev ${ifaces[$i]} root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
                    tc qdisc  add dev ${ifaces[$i]} parent 1:2 handle 12: netem delay ${delay}ms
                    tc filter add dev ${ifaces[$i]} parent 1:0 protocol ip prio 1 u32 match ip dst $IP_AQM_C flowid 1:1
                fi"
        done
    else
        # no delay: force pfifo_fast
        hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT)
        ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB)
        for i in ${!hosts[@]}; do
            ssh root@${hosts[$i]} "
                # skip if already set up
                if ! tc qdisc show dev ${ifaces[$i]} | grep -q 'qdisc pfifo_fast 1:'; then
                    tc qdisc del dev ${ifaces[$i]} root 2>/dev/null || true
                    tc qdisc add dev ${ifaces[$i]} root handle 1: pfifo_fast 2>/dev/null || true
                fi"
        done
    fi
}

configure_clients_edge() {
    local testrate=$1
    local rtt=$2
    local aqm_name=$3
    local aqm_params=$4

    configure_clients_edge_aqm_node $testrate $rtt $aqm_name "$aqm_params"
    configure_clients_node $rtt
}

configure_server_edge() {
    local ip_server_mgmt=$1
    local ip_aqm_s=$2
    local iface_server=$3
    local iface_on_server=$4
    local rtt=$5

    local delay=$(echo "scale=2; $rtt / 2" | bc)  # delay is half the rtt

    # put traffic in band 1 by default
    # delay traffic in band 1
    # filter traffic from aqm node itself into band 0 for priority and no delay
    if tc qdisc show dev $iface_server | grep -q 'qdisc netem 12:'; then
        tc qdisc change dev $iface_server handle 12: netem delay ${delay}ms
    else
        tc qdisc  del dev $iface_server root 2>/dev/null || true
        tc qdisc  add dev $iface_server root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
        tc qdisc  add dev $iface_server parent 1:2 handle 12: netem delay ${delay}ms # todo: put "limit" ?
        tc filter add dev $iface_server parent 1:0 protocol ip prio 1 u32 match ip src $ip_aqm_s flowid 1:1
    fi

    ssh root@$ip_server_mgmt "
        if tc qdisc show dev $iface_on_server | grep -q 'qdisc netem 12:'; then
            tc qdisc change dev $iface_on_server handle 12: netem delay ${delay}ms
        else
            tc qdisc  del dev $iface_on_server root 2>/dev/null || true
            tc qdisc  add dev $iface_on_server root       handle  1: prio bands 2 priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
            tc qdisc  add dev $iface_on_server parent 1:2 handle 12: netem delay ${delay}ms
            tc filter add dev $iface_on_server parent 1:0 protocol ip prio 1 u32 match ip dst $ip_aqm_s flowid 1:1
        fi"
}

reset_aqm_client_edge() {
    # reset qdisc at client side
    tc qdisc del dev $IFACE_CLIENTS root 2>/dev/null || true
    tc qdisc add dev $IFACE_CLIENTS root handle 1: pfifo_fast 2>/dev/null || true
}

reset_aqm_server_edge() {
    # reset qdisc at server side
    for iface in $IFACE_SERVERA $IFACE_SERVERB; do
        tc qdisc del dev $iface root 2>/dev/null || true
        tc qdisc add dev $iface root handle 1: pfifo_fast 2>/dev/null || true
    done
}

reset_host() {
    local host=$1
    local iface=$2 # the iface is the one that test traffic to aqm is going on
                   # e.g. $IFACE_ON_CLIENTA
    ssh root@$host "
        tc qdisc del dev $iface root 2>/dev/null || true
        tc qdisc add dev $iface root handle 1: pfifo_fast 2>/dev/null || true"
}

reset_all_hosts_edge() {
    hosts=($IP_CLIENTA_MGMT $IP_CLIENTB_MGMT $IP_SERVERA_MGMT $IP_SERVERB_MGMT)
    ifaces=($IFACE_ON_CLIENTA $IFACE_ON_CLIENTB $IFACE_ON_SERVERA $IFACE_ON_SERVERB)

    for i in ${!hosts[@]}; do
        reset_host ${hosts[$i]} ${ifaces[$i]}
    done
}

reset_all_hosts_cc() {
    for host in CLIENTA CLIENTB SERVERA SERVERB; do
        name="IP_${host}_MGMT"
        configure_host_cc ${!name} cubic 2
    done
}

get_host_cc() {
    local host=$1

    # see configure_host_cc for more details on setup

    ssh root@$host '
        if [ -f /proc/sys/net/ipv4/tcp_congestion_control ]; then
            sysctl -n net.ipv4.tcp_congestion_control
            sysctl -n net.ipv4.tcp_ecn
        else
            # we are on docker
            . /tmp/testbed-vars-local.sh
            if ip a show $IFACE_AQM | grep -q 10.25.1.; then
                # on client
                route=10.25.2.0/24
            else
                route=10.25.1.0/24
            fi

            ip route show $route | awk -F"congctl " "{print \$2}" | cut -d" " -f1
            ip route show $route | grep -q "ecn" && echo "1" || echo "2"
        fi'
}

get_aqm_options() {
    local aqm_name=$1

    if [ -n "$aqm_name" ]; then
        tc qdisc show dev $IFACE_CLIENTS | grep "$aqm_name" | sed 's/.*parent [0-9:]\+ //'
    else
        echo '(no aqm)'
    fi
}

# method that will abort the script if we are not on the aqm-machine
require_on_aqm_node() {
    if ! [[ $(ip addr show to $IP_AQM_C) ]]; then
        echo "The program must be run on the AQM-machine"
        exit 1
    fi
}

# initialize tmux environment
# call this before using run_fg and run_bg to initialize variables
# global variables:
# - $tmux_win_id
tmux_init() {
    # we use tmux to spawn other processes, easier to monitor them and avoid dead/zombie terminal
    if [ -z $TMUX ]; then
        >&2 echo "Please run this inside a tmux session"
        exit 1
    fi

    tmux_win_id=$(tmux display-message -p '#{window_id}')
    tmux set-window-option -t $tmux_win_id remain-on-exit on
    tmux_kill_dead_panes
}

# run a command in a foreground tmux pane
# global variables:
# - $tmux_win_id
# - $ret
# stores the pane pid in $ret
run_fg() {
    if [ -z $tmux_win_id ]; then
        >&2 echo "Tmux variables not initialized"
        >&2 echo "Call tmux_init first"
        exit 1
    fi

    local cmd="$1"
    local pane_pid=$(tmux split-window -dP -t $tmux_win_id -F '#{pane_pid}' "$cmd")
    tmux select-layout -t $tmux_win_id tiled

    ret="$pane_pid"
}

run_fg_verbose() {
    printf '%s\n' "$1"
    run_fg "$1"
}

# run a command in a background tmux pane
# global variables:
# - $tmux_win_id
# - $ret
# stores the pane pid in $ret
run_bg() {
    if [ -z $tmux_win_id ]; then
        >&2 echo "Tmux variables not initialized"
        >&2 echo "Call tmux_init first"
        exit 1
    fi

    local cmd="$1"

    # create the window if needed
    # output in the end should be the new pid of the running command
    # so that we can stop it later
    if [ -z "$tmux_bg_win_id" ] || ! tmux list-windows -F '#{window_id}' | grep -q "$tmux_bg_win_id"; then
        local res=$(tmux new-window -dP -F '#{window_id} #{pane_pid}' "$cmd")
        tmux_bg_win_id=$(echo "$res" | awk '{print $1}')
        tmux set-window-option -t $tmux_bg_win_id remain-on-exit on
        local pane_pid=$(echo "$res" | awk '{print $2}')
    else
        local pane_pid=$(tmux split-window -dP -t $tmux_bg_win_id -F '#{pane_pid}' "$cmd")
        tmux select-layout -t $tmux_bg_win_id tiled
    fi

    ret="$pane_pid"
}

run_bg_verbose() {
    printf '%s\n' "$1"
    run_bg "$1"
}

# kill dead panes in the active tmux session
tmux_kill_dead_panes() {
    tmux list-panes -s -F '#{pane_dead} #{pane_id}' \
        | grep ^1 | awk '{print $2}' | xargs -rL1 tmux kill-pane -t
}
