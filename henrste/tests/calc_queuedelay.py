#!/usr/bin/env python3

# this file generates queue statistics for _each_ sample
# the results are saved to:
# - qs_samples_ecn
# - qs_samples_nonecn
# with the format
# - sample_id max average p25 p99

import numpy as np

class QueueDelay():
    def parseLine(self, line):
        arr = np.array([])

        qs = 0
        for num in line.split():
            num = int(num)
            if num > 0:
                arr = np.concatenate([arr, np.full(num, qs, np.dtype('int64'))])

            qs += 1

        return arr

    def generateStats(self, numbers):
        res = [np.max(numbers).astype('str'),
               np.average(numbers).astype('str'),
               np.percentile(numbers, 25, interpolation='lower').astype('str'),
               np.percentile(numbers, 99, interpolation='lower').astype('str')]

        return ' '.join(res)

    def processTest(self, folder):
        with open(folder + '/qs_samples_nonecn', 'w') as fout:
            with open(folder + '/qs_ecn00_s', 'r') as f:
                f.readline()  # skip header

                for line in f:
                    fout.write('%s %s\n' % (line.split()[0], self.generateStats(
                            self.parseLine(line))))

        with open(folder + '/qs_samples_ecn', 'w') as fout:
            f1 = open(folder + '/qs_ecn01_s', 'r')
            f2 = open(folder + '/qs_ecn10_s', 'r')
            f3 = open(folder + '/qs_ecn11_s', 'r')

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