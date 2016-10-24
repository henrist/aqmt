#!/bin/bash

# this script generates udp traffic

cd "$(dirname $(readlink -f $BASH_SOURCE))"
. ../common.sh

# used to get output from functions without using subshells
# basicly just a return value container
ret=""

result_folder="res"

require_on_aqm_node

pids_to_kill=()
kill_known_pids() {
    for pid in "${pids_to_kill[@]}"; do
        kill $pid 2>/dev/null
    done
    pids_to_kill=()
}

analyze_results() {
    local folder=$1
    local link_rate_bits=$2

    local fairness="e"         # used to calculate rPDF, we don't use it now
    local nbrf=0               # used to calculate rPDF, we don't use it now
    local rtt_l4s=50           # used to calculate window size, we don't use it now
    local rtt_classic=50       # used to calculate window size, we don't use it now
    local nbr_l4s_flows=1      # used to generate rPDF and dmPDF, we don't use it now
    local nbr_classic_flows=1  # used to generate rPDF and dmPDF, we don't use it now
    (set -x; ../../traffic_analyzer/calc_henrste $folder $fairness $nbrf $link_rate_bits $rtt_l4s $rtt_classic $nbr_l4s_flows $nbr_classic_flows)
}

run_greedy() {
    local server_port=$traffic_port
    traffic_port+=1

    run_bg_verbose "ssh -t $IP_SERVERB_MGMT /opt/testbed/greedy_generator/greedy -vv -s $server_port"
    pids_to_kill+=($ret)

    run_bg_verbose "sleep 0.2; ssh -t $IP_CLIENTB_MGMT /opt/testbed/greedy_generator/greedy -vv $IP_SERVERB $server_port"
    pids_to_kill+=($ret)
}

run_udp() {
    #local server_port=$1
    local bitrate=$1 # in bits/sec
    local tos="" # ect0 = ECT(0), ect1 = ECT(1), all other is Non-ECT

    if [ "$2" == "ect1" ]; then
        tos="--tos 0x01" # ECT(1)
    elif [ "$2" == "ect0" ]; then
        tos="--tos 0x02" # ECT(0)
    fi

    local server_port=$traffic_port
    traffic_port+=1

    run_bg_verbose "ssh -t $IP_CLIENTA_MGMT iperf -s -p $server_port"
    pids_to_kill+=($ret)

    # bitrate to iperf is the udp data bitrate, not the ethernet frame size as we want
    local framesize=1514
    local headers=42
    bitrate=$(($bitrate * ($framesize-$headers) / $framesize))

    run_bg_verbose "sleep 0.5; ssh -t $IP_SERVERA_MGMT iperf -c $IP_CLIENTA -p $server_port $tos -u -l $(($framesize-$headers)) -R -b $bitrate -i 1 -t 99999"
    pids_to_kill+=($ret)
}

run_speedometer() {
    local delay=$1
    local bps=$(($2/8)) # speedometer uses bytes/s
    run_fg_verbose "speedometer -s -i $delay -l -t $IFACE_CLIENTS -m $2"
    pids_to_kill+=($ret)
}

run_ta_and_wait() {
    local PCAPFILTER="ip and dst net $(echo $IP_AQM_C | sed 's/\.[0-9]\+$/.0/')/24 and (tcp or udp)"
    local ipclass=f
    run_fg_verbose "echo 'Idling a bit before running ta...'; sleep 10; ../../traffic_analyzer/ta $IFACE_CLIENTS '${PCAPFILTER}' $result_folder 500 $ipclass 200"
    #run_fg_verbose "../../traffic_analyzer/ta $IFACE_CLIENTS '${PCAPFILTER}' $result_folder 3000 $ipclass"

    # we add it to the kill list in case the script is terminated
    pids_to_kill+=($ret)
    local ta_pid="$ret"

    # wait until 'ta' quits
    while kill -0 $ta_pid 2>/dev/null; do
        sleep .4
    done
}

run_monitor_setup() {
    run_fg_verbose "watch -n .2 ../show_setup.sh -vir $IFACE_CLIENTS"
    pids_to_kill+=($ret)
}

configure_testbed() {
    printf 'Configuring testbed\n'

    reset_aqm_client_edge
    reset_aqm_server_edge
    reset_all_hosts_edge
    reset_all_hosts_cc

    local testrate=10Mbit

    local rtt_clients=0 # in ms
    local rtt_servera=50 # in ms
    local rtt_serverb=50 # in ms

    local aqm_name=
    local aqm_params=

    #local aqm_name=red
    #local aqm_params="limit 1000000 avpkt 1000 ecn adaptive bandwidth $testrate"

    #local aqm_name=dualq
    #local aqm_params="l_thresh_us 1000 offset 0 l_slope 5 c_slope 4 l_smooth 0 c_smooth 5 l_power 1 c_power 2 l_shift 50"

    local aqm_name=pi2
    local aqm_params="dualq limit 100" # l_thresh 10000"

    configure_clients_edge $testrate $rtt_clients $aqm_name "$aqm_params"
    configure_server_edge $IP_SERVERA_MGMT $IP_AQM_SA $IFACE_SERVERA $IFACE_ON_SERVERA $rtt_servera
    configure_server_edge $IP_SERVERB_MGMT $IP_AQM_SB $IFACE_SERVERB $IFACE_ON_SERVERB $rtt_serverb

    # congestion control
    #   example configurations:
    #     reno 2
    #     dctcp 1
    #     cubic 1 (set as default when reset)
    configure_host_cc $IP_CLIENTA_MGMT cubic 2
    configure_host_cc $IP_SERVERA_MGMT cubic 2
    configure_host_cc $IP_CLIENTB_MGMT dctcp 1
    configure_host_cc $IP_SERVERB_MGMT dctcp 1
}

clean_up() {
    kill_known_pids
    tmux_kill_dead_panes
    exit
}

tmux_init

trap clean_up SIGHUP SIGINT SIGTERM

configure_testbed



step_pre() {
    # directory we store test results
    rm -R "$result_folder"
    mkdir -p "$result_folder"
}

step_post() {
    run_monitor_setup
    run_speedometer 0.05 $((11000*1000/8))

    run_ta_and_wait
    kill_known_pids

    analyze_results "$result_folder" $((10000*1000))

    sleep 1
    tmux_kill_dead_panes
}


#    truncate -s0 "$set_folder/setup"
#    printf "rtt_clients 0\n" >>"$set_folder/setup"
#    printf "rtt_a 50\n" >>"$set_folder/setup"
#    printf "rtt_b 50\n" >>"$set_folder/setup"
#    printf "cc_a cubic\ncc_b dctcp\n" >>"$set_folder/setup"
#    #printf "limit 100\n" >>"$set_folder/setup"
#    printf "aqm pi2\n" >>"$set_folder/setup"
#    printf "aqm_params dualq limit 100\n" >>"$set_folder/setup"
#    printf "rate 1000000\n" >>"$set_folder/setup"
#    printf "udp_type $udp_type\n" >>"$set_folder/setup"



speeds=(5000 9000 9500 10000 10500 11000 12000 12500 13000 13100 13200 13400 13500 14000 28000 50000 500000)
udp_types=("mix")

for udp_type_i in ${!udp_types[@]}; do
    udp_type=${udp_types[$udp_type_i]}
    set_folder="set-3-2" #$udp_type_i

    for speed_i in ${!speeds[@]}; do
        result_folder="$set_folder/res-$speed_i"
        step_pre

        truncate -s0 "$result_folder/setup"
        printf "udp_rate $((${speeds[$speed_i]}*1000))\n" >>"$result_folder/setup"
        printf "udp_type %s\n" $udp_type >>"$result_folder/setup"

        run_greedy

        if [ "$udp_type" = "mix" ]; then
            run_udp $((${speeds[$speed_i]}*1000/2)) "nonect"
            run_udp $((${speeds[$speed_i]}*1000/2)) "ect0"
        else
            run_udp $((${speeds[$speed_i]}*1000)) "$udp_type"
        fi

        step_post
    done
done