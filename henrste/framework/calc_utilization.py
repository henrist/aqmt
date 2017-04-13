#!/usr/bin/env python3

# this file generates total utilization statistics for _each_ sample
# the results are saved to:
# - util

import os
import sys


def parse_line(line):
    return int(line.split()[2])


def process_test(folder, link_bitrate):
    outfolder = folder + '/derived'
    if not os.path.exists(outfolder):
        os.makedirs(outfolder)

    with open(outfolder + '/util', 'w') as fout:
        fout.write('# sample_id total_util_in_percent ecn_util_in_percent nonecn_util_in_percent\n')

        f1 = open(folder + '/ta/r_tot_ecn', 'r')
        f2 = open(folder + '/ta/r_tot_nonecn', 'r')

        # all files should have the same amount of lines
        for line1 in f1:
            line2 = f2.readline()

            # skip comments
            if line1[0] == '#':
                continue

            r_ecn = parse_line(line1)
            r_nonecn = parse_line(line2)
            r_tot = r_ecn + r_nonecn

            fout.write('%s %f %f %f\n' % (
                line1.split()[0],
                r_tot / link_bitrate,
                r_ecn / link_bitrate,
                r_nonecn / link_bitrate
            ))

        f1.close()
        f2.close()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('%s <testfolder> <bitrate_in_bits>' % sys.argv[0])

    else:
        process_test(sys.argv[1], int(sys.argv[2]))
        print('Generated util')
