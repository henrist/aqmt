#!/usr/bin/env python3

# this file generates utilization statistics for _each_ sample
# the results are saved to:
# - util
# with the format
# - sample_id total_util_in_percent ecn_util_in_percent nonecn_util_in_percent

import sys

class Utilization():
    def parseLine(self, line):
        return int(line.split()[2])

    def processTest(self, folder, link_bitrate):
        with open(folder + '/util', 'w') as fout:
            f1 = open(folder + '/r_tot_ecn', 'r')
            f2 = open(folder + '/r_tot_nonecn', 'r')

            # all files should have the same amount of lines
            for line1 in f1:
                line2 = f2.readline()

                # skip comments
                if line1[0] == '#':
                    continue

                r_ecn = self.parseLine(line1)
                r_nonecn = self.parseLine(line2)
                r_tot = r_ecn + r_nonecn

                fout.write('%s %f %f %f\n' % (line1.split()[0],
                        r_tot / link_bitrate,
                        r_ecn / link_bitrate,
                        r_nonecn / link_bitrate))

            f1.close()
            f2.close()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('%s <testfolder> <bitrate_in_bits>' % sys.argv[0])

    else:
        u = Utilization()
        u.processTest(sys.argv[1], int(sys.argv[2]))
        print('Generated util')
