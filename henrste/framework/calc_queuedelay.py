#!/usr/bin/env python3

# this file generates packets in queue statistics for _each_ sample
# the results are saved to:
# - queue_packets_ecn_samplestats
# - queue_packets_nonecn_samplestats

import numpy as np
import os
import sys


def parse_header(line):
    """
    The header in queue_packets_ecnXX_s contains the queueing delay in us that
    this column represents.

    The first column in the header contains number of columns following.
    We simply ignore this.
    """
    return np.fromstring(line, dtype=int, sep=' ')[1:]


def parse_line(line, header_us):
    num = np.fromstring(line, dtype=int, sep=' ')[1:]
    return np.repeat(header_us, num)


def generate_stats(numbers):
    if numbers.size == 0:
        res = ['-', '-', '-', '-', '-', '-', '-', '-', '-']
    else:
        res = [
            np.average(numbers).astype('str'),
            '-',  # not used: np.std(numbers).astype('str'),
            np.min(numbers).astype('str'),
            np.percentile(numbers, 1, interpolation='lower').astype('str'),
            np.percentile(numbers, 25, interpolation='lower').astype('str'),
            np.percentile(numbers, 50, interpolation='lower').astype('str'),
            np.percentile(numbers, 75, interpolation='lower').astype('str'),
            np.percentile(numbers, 99, interpolation='lower').astype('str'),
            np.max(numbers).astype('str'),
        ]

    return ' '.join(res)


def process_test(folder):
    if not os.path.exists(folder + '/derived'):
        os.makedirs(folder + '/derived')

    with open(folder + '/derived/queue_nonecn_samplestats', 'w') as fout:
        fout.write('#average stddev min p1 p25 p50 p75 p99 max\n')
        with open(folder + '/ta/queue_packets_ecn00', 'r') as f:
            header_us = parse_header(f.readline())

            for line in f:
                fout.write('%s %s\n' % (
                    line.split()[0],  # time of sample
                    generate_stats(
                        parse_line(line, header_us)
                    )
                ))

    with open(folder + '/derived/queue_ecn_samplestats', 'w') as fout:
        fout.write('#average stddev min p1 p25 p50 p75 p99 max\n')

        f1 = open(folder + '/ta/queue_packets_ecn01', 'r')
        f2 = open(folder + '/ta/queue_packets_ecn10', 'r')
        f3 = open(folder + '/ta/queue_packets_ecn11', 'r')

        header_us = parse_header(f1.readline())
        f2.readline()  # skip the other headers, they should be same
        f3.readline()

        # all files should have the same amount of lines
        for line1 in f1:
            line2 = f2.readline()
            line3 = f3.readline()

            fout.write('%s %s\n' % (
                line1.split()[0],  # time of sample
                generate_stats(
                    np.concatenate([
                        parse_line(line1, header_us),
                        parse_line(line2, header_us),
                        parse_line(line3, header_us)
                    ])
                )
            ))

        f1.close()
        f2.close()
        f3.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: %s <test_folder>', sys.argv[0])
    process_test(sys.argv[1])
