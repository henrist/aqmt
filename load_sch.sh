#!/bin/sh

for n in sch_fifo_qsize sch_pi2 sch_pie_qsize; do (
    echo
    echo "---- BUILDING AND LOADING: $n ----"
    echo
    cd $n
    make
    sudo make unload
    sudo make load
); done
