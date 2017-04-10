#!/bin/bash

cd "$(dirname $(readlink -f $BASH_SOURCE))"

(
    echo
    echo "---- BUILDING: traffic_analyzer ----"
    echo
    cd traffic_analyzer
    make
)

(
    echo
    echo "---- BUILDING: greedy_generator ----"
    echo
    cd greedy_generator
    make
)

for n in sch_fifo_latest_qsize sch_pi2 sch_pie_latest_qsize sch_fq_codel_latest_qsize tcp_dctcp; do (
    echo
    echo "---- BUILDING AND LOADING: $n ----"
    echo
    cd $n
    make clean
    make
    sudo make unload >/dev/null 2>&1
    sudo make load
); done
