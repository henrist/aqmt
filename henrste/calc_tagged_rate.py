#!/usr/bin/env python3

# this file generates rate statistics for the different tagget traffic streams
#
# as all the test traffic uses different ports we don't need to worry
# about which nodes that sends traffic
#
# the results are saved to:
# - r_tagged
# - r_tagged_stats
# - util_tagged
# - util_tagged_stats

import numpy as np
import re
import sys

class TaggedRate():
    DEFAULT_TAG='Other'

    def generateStats(self, numbers):
        if len(numbers) == 0:
            res = ['0', '0', '0', '0', '0', '0', '0']
        else:
            res = [np.min(numbers).astype('str'),
                   np.percentile(numbers, 1, interpolation='lower').astype('str'),
                   np.percentile(numbers, 25, interpolation='lower').astype('str'),
                   np.average(numbers).astype('str'),
                   np.percentile(numbers, 75, interpolation='lower').astype('str'),
                   np.percentile(numbers, 99, interpolation='lower').astype('str'),
                   np.max(numbers).astype('str')]

        return ' '.join(res)

    def saveTagRates(self, folder, rates):
        with open(folder + '/r_tagged', 'w') as fall:
            fall.write('#sample rate\n')

            with open(folder + '/r_tagged_stats', 'w') as fstats:
                fstats.write('#tag min p1 p25 mean p75 p99 max\n')

                first = True
                for tag, values in rates.items():
                    if not first:
                        fall.write('\n\n')
                    first = False
                    fall.write('"%s"\n' % tag)

                    for i, rate in enumerate(values):
                        fall.write('%d %d\n' % (i, rate))

                    fstats.write('"%s" %s\n' % (tag, self.generateStats(values)))

    def saveTagUtil(self, folder, rates, bitrate):
        with open(folder + '/util_tagged', 'w') as fall:
            fall.write('#sample util\n')

            with open(folder + '/util_tagged_stats', 'w') as fstats:
                fstats.write('#tag min p1 p25 mean p75 p99 max\n')

                first = True
                for tag, values in rates.items():
                    list_util = []

                    if not first:
                        fall.write('\n\n')
                    first = False
                    fall.write('"%s"\n' % tag)

                    for i, rate in enumerate(values):
                        util = rate / bitrate
                        list_util.append(util)

                        fall.write('%d %f\n' % (i, util))

                    fstats.write('"%s" %s\n' % (tag, self.generateStats(list_util)))

    def getRates(self, folder, flows, tags, bitrate):
        """Map all known rates to the tag and aggregated rate"""

        rates = {self.DEFAULT_TAG: []}
        for tag in tags:
            rates[tag] = []

        for ecntype in ['ecn', 'nonecn']:
            n_samples = 0
            with open(folder + '/r_pf_' + ecntype) as f:
                #0 1000 6152397 3693860
                for line in f:
                    n_samples += 1

                    for i, rate in enumerate(line.split()[2:]):
                        tag = flows[ecntype][i]['tag']

                        if len(rates[tag]) < n_samples:
                            rates[tag].append(0)

                        rates[tag][n_samples-1] += int(rate)

        # remove unknown if all is tagged
        if len(rates[self.DEFAULT_TAG]) == 0:
            rates.pop(self.DEFAULT_TAG)

        # make sure all lists are filled up
        # (in case no traffic is detected on a tag)
        for tag in tags:
            if len(rates[tag]) == 0:
                rates[tag] = [0] * n_samples

        return rates

    def extractProperties(self, line):
        """Convert the line in the 'details' file to a map"""
        list = {}
        name = None

        for item in re.split(r'(?:^| )([^= ]+=)', line.strip()):
            if item.endswith('='):
                name = item[0:-1]
            elif name is not None:
                list[name] = item

        return list

    def getClassification(self, folder):
        tags = set()
        classify = []

        with open(folder + '/details', 'r') as f:
            for line in f:
                if line.startswith('traffic='):
                    properties = self.extractProperties(line)
                    if 'tag' in properties:
                        tag = properties['tag']
                        tags.add(tag)

                        classify_by = 'client' if 'client' in properties else 'server'
                        classify.append({classify_by: properties[classify_by], 'tag': tag})

        return [list(tags), classify]

    def getBitrate(self, folder):
        with open(folder + '/details', 'r') as f:
            for line in f:
                if line.startswith('testbed_rate '):
                    return int(line.split(' ')[1])

        raise Exception('Could not determine bitrate used in test')

    def getFlows(self, folder, classify):
        flows = {'ecn': [], 'nonecn': []}
        for ecntype in ['ecn', 'nonecn']:
            with open(folder + '/flows_' + ecntype) as f:
                for line in f:
                    #TCP 10.25.2.21 5504 10.25.1.11 53898
                    type, srcip, srcport, dstip, dstport = line.split()

                    # identify the tag
                    tag = self.DEFAULT_TAG
                    for item in classify:
                        if 'client' in item and item['client'] == dstport:
                            tag = item['tag']
                            break
                        elif 'server' in item and item['server'] == srcport:
                            tag = item['tag']
                            break

                    flows[ecntype].append({
                        'flow': line.strip(),
                        'tag': tag
                    })

        return flows

    def processTest(self, folder):
        tags, classify = self.getClassification(folder)
        bitrate = self.getBitrate(folder)
        flows = self.getFlows(folder, classify)

        rates = self.getRates(folder, flows, tags, bitrate)

        self.saveTagRates(folder, rates)
        self.saveTagUtil(folder, rates, bitrate)


if __name__ == '__main__':
    qd = TaggedRate()
    qd.processTest('testsets/fairness/pi2/dctcp-vs-dctcp/test-rtt-100')
