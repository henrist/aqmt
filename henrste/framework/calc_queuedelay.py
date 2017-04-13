#!/usr/bin/env python3

# this file generates queue statistics for _each_ sample
# the results are saved to:
# - qs_samples_ecn
# - qs_samples_nonecn

import numpy as np
import os

class QueueDelay():
    def parseHeader(self, line):
        """
        The header in qs_ecnXX_s contains the queueing delay in us that
        this column represents.

        The first column in the header contains number of columns following.
        We simply ignore this.
        """
        return np.fromstring(line, dtype=int, sep=' ')[1:]

    def parseLine(self, line, header_us):
        arr = np.array([])

        num = np.fromstring(line, dtype=int, sep=' ')[1:]
        arr = np.repeat(header_us, num)

        return arr

    def generateStats(self, numbers):
        if numbers.size == 0:
            res = ['0', '0', '0', '0', '0', '0', '0', '0', '0']
        else:
            res = [
                np.average(numbers).astype('str'),
                '-', # not used: np.std(numbers).astype('str'),
                np.min(numbers).astype('str'),
                np.percentile(numbers, 1, interpolation='lower').astype('str'),
                np.percentile(numbers, 25, interpolation='lower').astype('str'),
                np.percentile(numbers, 50, interpolation='lower').astype('str'),
                np.percentile(numbers, 75, interpolation='lower').astype('str'),
                np.percentile(numbers, 99, interpolation='lower').astype('str'),
                np.max(numbers).astype('str'),
            ]

        return ' '.join(res)

    def processTest(self, folder):
        outfolder = folder + '/derived'
        if not os.path.exists(outfolder):
            os.makedirs(outfolder)

        with open(outfolder + '/qs_samples_nonecn', 'w') as fout:
            fout.write('#average stddev min p1 p25 p50 p75 p99 max\n')
            with open(folder + '/ta/qs_ecn00_s', 'r') as f:
                header_us = self.parseHeader(f.readline())

                for line in f:
                    fout.write('%s %s\n' % (
                        line.split()[0],  # time of sample
                        self.generateStats(
                            self.parseLine(line, header_us)
                        )
                    ))

        with open(outfolder + '/qs_samples_ecn', 'w') as fout:
            fout.write('#average stddev min p1 p25 p50 p75 p99 max\n')

            f1 = open(folder + '/ta/qs_ecn01_s', 'r')
            f2 = open(folder + '/ta/qs_ecn10_s', 'r')
            f3 = open(folder + '/ta/qs_ecn11_s', 'r')

            header_us = self.parseHeader(f1.readline())
            f2.readline()  # skip the other headers, they should be same
            f3.readline()

            # all files should have the same amount of lines
            for line1 in f1:
                line2 = f2.readline()
                line3 = f3.readline()

                fout.write('%s %s\n' % (
                    line1.split()[0],  # time of sample
                    self.generateStats(
                        np.concatenate([
                            self.parseLine(line1, header_us),
                            self.parseLine(line2, header_us),
                            self.parseLine(line3, header_us)
                        ])
                    )
                ))

            f1.close()
            f2.close()
            f3.close()


if __name__ == '__main__':
    qd = QueueDelay()
    qd.processTest('testset-a/test-001')
