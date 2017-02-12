#!/usr/bin/env python3

# this file generates queue statistics for _each_ sample
# the results are saved to:
# - qs_samples_ecn
# - qs_samples_nonecn

import numpy as np
import os

class QueueDelay():
    def parseLine(self, line):
        arr = np.array([])

        num = np.fromstring(line, dtype=int, sep=' ')[1:]
        qs = np.arange(0, num.size)
        arr = np.repeat(qs, num)

        return arr

    def generateStats(self, numbers):
        if numbers.size == 0:
            res = ['0', '0', '0', '0', '0']
        else:
            res = [np.min(numbers).astype('str'),
                   np.percentile(numbers, 25, interpolation='lower').astype('str'),
                   np.average(numbers).astype('str'),
                   np.percentile(numbers, 99, interpolation='lower').astype('str'),
                   np.max(numbers).astype('str')]

        return ' '.join(res)

    def processTest(self, folder):
        outfolder = folder + '/derived'
        if not os.path.exists(outfolder):
            os.makedirs(outfolder)

        with open(outfolder + '/qs_samples_nonecn', 'w') as fout:
            fout.write('# min p25 average p99 max\n')
            with open(folder + '/ta/qs_ecn00_s', 'r') as f:
                f.readline()  # skip header

                for line in f:
                    fout.write('%s %s\n' % (line.split()[0], self.generateStats(
                            self.parseLine(line))))

        with open(outfolder + '/qs_samples_ecn', 'w') as fout:
            fout.write('# min p26 average p99 max\n')

            f1 = open(folder + '/ta/qs_ecn01_s', 'r')
            f2 = open(folder + '/ta/qs_ecn10_s', 'r')
            f3 = open(folder + '/ta/qs_ecn11_s', 'r')

            f1.readline()  # skip header
            f2.readline()
            f3.readline()

            # all files should have the same amount of lines
            for line1 in f1:
                line2 = f2.readline()
                line3 = f3.readline()

                fout.write('%s %s\n' % (line1.split()[0], self.generateStats(
                        np.concatenate([
                            self.parseLine(line1),
                            self.parseLine(line2),
                            self.parseLine(line3)
                        ]))))

            f1.close()
            f2.close()
            f3.close()


if __name__ == '__main__':
    qd = QueueDelay()
    qd.processTest('testset-a/test-001')
