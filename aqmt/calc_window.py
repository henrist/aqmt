#!/usr/bin/env python3
#
# This file generates an estimation of window size for the
# two queues for _each_ sample. It will not be exact, and
# it's correctness will vary with the variation of queue delay
# in the queue.
#
# The results are saved to:
# - derived/window
#   each line formatted as: <sample id> <window ecn in bits> <window nonecn in bits>
#
# Dependency:
# - calc_queuedelay.py (for per sample queue stats)

import os
import sys


def get_rates(rate_file):
    rates = []

    with open(rate_file, 'r') as f:
        for line in f:
            # skip comments
            if line[0] == '#':
                continue

            # format of rate file:
            # <sample id> <sample time> <rate in b/s>

            rates.append(int(line.split()[2]))

    return rates


def get_rtts_with_queue(queue_file, base_rtt):
    rtts = []

    with open(queue_file, 'r') as f:
        for line in f:
            # skip comments
            if line[0] == '#':
                continue

            # format of queue file:
            # <sample time> <average_in_us> ...
            # the average might be '-' if it is unknown
            queue_avg = line.split()[1]
            queue_avg = 0 if queue_avg == '-' else float(queue_avg)

            # add rtt and normalize to seconds
            # base rtt is in ms
            rtts.append((queue_avg / 1000 + base_rtt) / 1000)

    return rtts


def calc_window(rates, rtts_s):
    windows = []

    # all data should have same amount of samples
    for i, rate in enumerate(rates):
        rtt = rtts_s[i]  # rtt in seconds

        windows.append(rate * rtt)

    return windows


def write_window(file, window_ecn_list, window_nonecn_list):
    with open(file, 'w') as f:
        f.write('#sample_id window_ecn_in_bits window_nonecn_in_bits\n')

        for i, window_ecn in enumerate(window_ecn_list):
            window_nonecn = window_nonecn_list[i]

            f.write('%d %d %d\n' % (i, window_ecn, window_nonecn))


def process_test(folder, base_rtt_ecn_ms, base_rtt_nonecn_ms):
    write_window(
        folder + '/derived/window',
        calc_window(
            get_rates(folder + '/ta/rate_ecn'),
            get_rtts_with_queue(folder + '/derived/queue_ecn_samplestats', base_rtt_ecn_ms),
        ),
        calc_window(
            get_rates(folder + '/ta/rate_nonecn'),
            get_rtts_with_queue(folder + '/derived/queue_nonecn_samplestats', base_rtt_nonecn_ms),
        ),
    )


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: %s <test_folder> <rtt_ecn_ms> <rtt_nonecn_ms>' % sys.argv[0])
        sys.exit(1)

    process_test(
        sys.argv[1],
        float(sys.argv[2]),
        float(sys.argv[3]),
    )

    print('Generated win')
