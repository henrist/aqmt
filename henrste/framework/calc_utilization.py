#!/usr/bin/env python3

# this file generates total utilization statistics for _each_ sample
# the results are saved to:
# - util

import os
import sys


def parse_line(line):
    return int(line.split()[2])


def process_test(folder, link_bitrate):
    if not os.path.exists(folder + '/derived'):
        os.makedirs(folder + '/derived')

    with open(folder + '/derived/util', 'w') as fout:
        fout.write('# sample_id total_util_in_percent ecn_util_in_percent nonecn_util_in_percent\n')

        f1 = open(folder + '/ta/rate_ecn', 'r')
        f2 = open(folder + '/ta/rate_nonecn', 'r')

        # all files should have the same amount of lines
        for line1 in f1:
            line2 = f2.readline()

            # skip comments
            if line1[0] == '#':
                continue

            rate_ecn = parse_line(line1)
            rate_nonecn = parse_line(line2)
            rate_tot = rate_ecn + rate_nonecn

            fout.write('%s %f %f %f\n' % (
                line1.split()[0],
                rate_tot / link_bitrate,
                rate_ecn / link_bitrate,
                rate_nonecn / link_bitrate
            ))

        f1.close()
        f2.close()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: %s <test_folder> <bitrate_in_bits>' % sys.argv[0])

    else:
        process_test(sys.argv[1], int(sys.argv[2]))
        print('Generated util')
