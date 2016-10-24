
# ----------------
# proc do_header


    num=$(wc -l set-2-0/util_stats | awk '{print $1-1}')


    gpi="
reset
set terminal postscript eps enhanced color 'Times-Roman' 120
#set notitle
set key above
set key box linestyle 99
set key spacing 1.2
set grid xtics ytics ztics lw 0.2 lc rgb 'gray'
set size 12,10
#set size ratio 0.15
set boxwidth 0.2 absolute

set title 'Link capacity: 10 Mbit, 50 ms RTT, queue limit 100 packets'
set xlabel 'UDP bitrate [kbps]'

#set label 2 'RTT[ms]:' at screen 0.25,0.6 front font 'Times-Roman,120' tc rgb 'black' left
set xtic rotate by -65 offset 1
set style fill solid 1.0 border
set boxwidth 0.4
set xrange [-1:$(($num*2+3)).3]

# aqm name
#set label 30 'PI2' at screen 1,3.4 font 'Times-Roman,140' tc rgb 'black' left"



# end do_header
# ----------------


    color_cubic="#FC6C6C"
    color_dctcp="blue"
    color_udp_l4s="purple"
    color_ecn_cubic="black"
    color_reno="brown"
    color_util="orange"

    #gpi=$gpi"set xrange [-0.75:$x_count-1]"$'\n'

    #_$(date +%s)
    gpi+="
set output \"set-2-0/test_qd.eps\"
set ylabel \"Queue delay [ms]\"
set y2label 'Percent'
set yrange [0:]
set y2range [:]
set boxwidth 0.2
set y2tic 5

set style line 100 lt 1 lc rgb 'red' lw 2
set arrow 100 from 1,-1 to 1,1 nohead ls 100 front
set arrow 100 from graph 0, second 100 to graph 1, second 100 nohead ls 100 front

plot "


    offset=$(($num+1))


    gpi+="'set-2-0/qs_ecn_stats'    using (\$0+0.0):3:5:4:3:xtic(1)   with candlesticks ls 1 lw 35 lc      rgb '${color_dctcp}'         title 'DCTCP (L4S-queue)', "
    gpi+="'set-2-0/qs_nonecn_stats' using (\$0+0.3):3:5:4:3:xtic('')  with candlesticks ls 1 lw 35 lc      rgb '${color_reno}'          title 'UDP (classic-queue)', "
    gpi+="'set-2-0/util_stats'      using (\$0+0.15):3:5:4:3:xtic('')  axes x1y2 with candlesticks ls 1 lw 35 lc     rgb '${color_util}'         title 'Utilization', "
    gpi+="'set-2-0/d_percent_nonecn_stats'   using (\$0+0.45):3:5:4:3:xtic('')  axes x1y2 with candlesticks ls 1 lw 35 lc     rgb 'red'         title 'Drops classic', "

    #gpi+="'set-1/qs_ecn_stats'    using (\$0+$offset.0):3:5:4:3:xtic(1)   with candlesticks ls 1 lw 35 lc      rgb '${color_dctcp}'         title '', "
    #gpi+="'set-1/qs_nonecn_stats' using (\$0+$offset.3):3:5:4:3:xtic('')  with candlesticks ls 1 lw 35 lc      rgb '${color_udp_l4s}'          title 'UDP (L4S-queue)', "
    #gpi+="'set-1/util_stats'   using (\$0+$offset.15):3:5:4:3:xtic('')  axes x1y2 with candlesticks ls 1 lw 35 lc     rgb '${color_util}'         title '', "


    #:xtic(1)
    #gpi+="'set-0/qs_ecn_stats'    using (\$0+0.0):3:(\$4-\$3):xtic(1) with boxerrorbars ls 1 lw 10 lc      rgb '${color_dctcp}'         title \"${title_ecn_mean}\", "
    #gpi+="''                     using (\$0+0.0):4                   with points       ls 1 lw 10 pt 5 lc rgb '${color_dctcp}'    ps 3 title '', "
    #gpi+="'set-0/qs_nonecn_stats' using (\$0+0.3):3:(\$4-\$3)         with boxerrorbars ls 1 lw 10 lc      rgb '${color_reno}'          title \"${title_nonecn_mean}\", "
    #gpi+="''                     using (\$0+0.3):4                   with points       ls 1 lw 10 pt 5 lc rgb '${color_reno}'     ps 3 title '', "

    #gpi+="'set-0/res-2/qs_ecn_stats'    using (\$0+1.0):3:(\$4-\$3):xtic(1) with boxerrorbars ls 1 lw 10 lc rgb '${color_dctcp}'    title '',                       '' using (\$0+$gap1):4 with points ls 1 lw 10 pt 5 lc rgb '${color_dctcp}'    ps 3 title '', "
    #gpi+="'set-0/res-2/qs_nonecn_stats' using (\$0+1.3):3:(\$4-\$3)         with boxerrorbars ls 1 lw 10 lc rgb '${color_reno}'     title '',                       '' using (\$0+$gap2):4 with points ls 1 lw 10 pt 5 lc rgb '${color_reno}'     ps 3 title '', "

    #gpi+="'set-0/res-3/qs_ecn_stats'    using (\$0+2.0):3:(\$4-\$3):xtic(1) with boxerrorbars ls 1 lw 10 lc rgb '${color_dctcp}'    title '',                       '' using (\$0+$gap1):4 with points ls 1 lw 10 pt 5 lc rgb '${color_dctcp}'    ps 3 title '', "
    #gpi+="'set-0/res-3/qs_nonecn_stats' using (\$0+2.3):3:(\$4-\$3)         with boxerrorbars ls 1 lw 10 lc rgb '${color_reno}'     title '',                       '' using (\$0+$gap2):4 with points ls 1 lw 10 pt 5 lc rgb '${color_reno}'     ps 3 title '', "

    #gpi+="'set-0/res-4/qs_ecn_stats'    using (\$0+3.0):3:(\$4-\$3):xtic(1) with boxerrorbars ls 1 lw 10 lc rgb '${color_dctcp}'    title '',                       '' using (\$0+$gap1):4 with points ls 1 lw 10 pt 5 lc rgb '${color_dctcp}'    ps 3 title '', "
    #gpi+="'set-0/res-4/qs_nonecn_stats' using (\$0+3.3):3:(\$4-\$3)         with boxerrorbars ls 1 lw 10 lc rgb '${color_reno}'     title '',                       '' using (\$0+$gap2):4 with points ls 1 lw 10 pt 5 lc rgb '${color_reno}'     ps 3 title '', "


    #gpi+="'set-0/res-3/qs_ecn_stats'     using (\$0+3.0):3:5:4:3:xtic(1)    with candlesticks ls 1 lw 35  lc rgb '${color_dctcp}'  title '', "
    #gpi+="'set-0/res-3/qs_ecn_stats'     using (\$0+3.5):3:5:4:3            with candlesticks ls 1 lw 35  lc rgb '${color_util}'   title '', "

    echo "$gpi" > set-0/test_qd.gpi
	gnuplot set-0/test_qd.gpi
