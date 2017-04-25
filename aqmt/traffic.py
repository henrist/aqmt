"""
This file contains different functions for generating traffic for a test
"""

import os
from plumbum.cmd import ssh

from . import logger
from . import processes
from .terminal import get_log_cmd


def tcp_netcat(dry_run, testbed, hint_fn, run_fn, node='a', tag=None):
    """
    Run TCP traffic with netcat (nc)
    """
    node = 'A' if node == 'a' else 'B'
    server_port = testbed.get_next_traffic_port('SERVER%s' % node)

    hint_fn('traffic=tcp type=netcat node=%s%s server=%d tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

    cmd1 = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'cat /dev/zero | nc -l %d >/dev/null' % server_port]
    cmd2 = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'sleep 0.2; nc -d %s %d >/dev/null' % (os.environ['IP_SERVER%s' % node], server_port)]

    if dry_run:
        logger.debug(get_log_cmd(cmd1))
        logger.debug(get_log_cmd(cmd2))

        def stop_test():
            pass

    else:
        pid1 = run_fn(cmd1)
        pid2 = run_fn(cmd2)
        processes.add_known_pid(pid1)
        processes.add_known_pid(pid2)

        def stop_test():
            processes.kill_pid(pid1)
            processes.kill_pid(pid2)

    return stop_test


def tcp_iperf(dry_run, testbed, hint_fn, run_fn, node='a', tag=None):
    """
    Run TCP traffic with iperf2
    """
    node = 'A' if node == 'a' else 'B'
    server_port = testbed.get_next_traffic_port('CLIENT%s' % node)

    hint_fn('traffic=tcp type=iperf2 node=%s%s client=%d tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

    cmd1 = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'iperf -s -p %d' % server_port]
    cmd2 = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'sleep 0.2; iperf -c %s -p %d -t 86400' % (os.environ['IP_CLIENT%s' % node], server_port)]

    logger.debug(get_log_cmd(cmd1))
    logger.debug(get_log_cmd(cmd2))
    if dry_run:
        def stop_test():
            pass

    else:
        pid1 = run_fn(cmd1)
        pid2 = run_fn(cmd2)
        processes.add_known_pid(pid1)
        processes.add_known_pid(pid2)

        def stop_test():
            processes.kill_pid(pid1)
            processes.kill_pid(pid2)

    return stop_test


def scp(dry_run, testbed, hint_fn, run_fn, node='a', tag=None):
    """
    Run TCP traffic with SCP (SFTP)

    Note there are some issues with the window size inside
    SSH as it uses its own sliding window. This test is therefore
    not reliable with a high BDP

    See:
    - http://www.slideshare.net/datacenters/enabling-high-performance-bulk-data-transfers-with-ssh
    - http://stackoverflow.com/questions/8849240/why-when-i-transfer-a-file-through-sftp-it-takes-longer-than-ftp

    All traffic goes over port 22 as of now. Tagging is
    not really possible because of this.
    """
    server_port = -1

    node = 'A' if node == 'a' else 'B'

    hint_fn('traffic=tcp type=scp node=%s%s server=%s tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

    cmd = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'scp /opt/testbed/bigfile %s:/tmp/' % (os.environ['IP_CLIENT%s' % node])]

    logger.debug(get_log_cmd(cmd))
    if dry_run:
        def stop_test():
            pass

    else:
        pid_server = run_fn(cmd)
        processes.add_known_pid(pid_server)

        def stop_test():
            processes.kill_pid(pid_server)

    return stop_test


def greedy(dry_run, testbed, hint_fn, run_fn, node='a', tag=None):
    """
    Run greedy TCP traffic

    Requires https://github.com/henrist/greedy on the machines
    (Available in the Docker version by default)

    Greedy = always data to send, full frames

    node: a or b (a is normally classic traffic, b is normally l4s)

    Tagging makes it possible to map similar traffic from multiple tests,
    despite being different ports and setup

    Returns a lambda to stop the traffic
    """
    node = 'A' if node == 'a' else 'B'
    server_port = testbed.get_next_traffic_port('SERVER%s' % node)

    hint_fn('traffic=tcp type=greedy node=%s%s server=%s tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

    cmd1 = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'greedy -vv -s %d' % server_port]
    cmd2 = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'sleep 0.2; greedy -vv %s %d' % (os.environ['IP_SERVER%s' % node], server_port)]

    logger.debug(get_log_cmd(cmd1))
    logger.debug(get_log_cmd(cmd2))
    if dry_run:
        def stop_test():
            pass

    else:
        pid_server = run_fn(cmd1)
        pid_client = run_fn(cmd2)
        processes.add_known_pid(pid_server)
        processes.add_known_pid(pid_client)

        def stop_test():
            processes.kill_pid(pid_server)
            processes.kill_pid(pid_client)

    return stop_test


def udp(dry_run, testbed, hint_fn, run_fn, bitrate, node='a', ect="nonect", tag=None):
    """
    Run UDP traffic at a constant bitrate

    ect: ect0 = ECT(0), ect1 = ECT(1), all other is Non-ECT

    Tagging makes it possible to map similar traffic from multiple tests,
    despite being different ports and setup

    Returns a lambda to stop the traffic
    """

    tos = ''
    if ect == 'ect1':
        tos = "--tos 0x01"  # ECT(1)
    elif ect == 'ect0':
        tos = "--tos 0x02"  # ECT(0)
    else:
        ect = 'nonect'

    node = 'A' if node == 'a' else 'B'
    server_port = testbed.get_next_traffic_port('CLIENT%s' % node)

    hint_fn('traffic=udp node=%s%s client=%s rate=%d ect=%s tag=%s' % (node, node, server_port, bitrate, ect, 'No-tag' if tag is None else tag))

    cmd_server = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'iperf -s -p %d' % server_port]

    # bitrate to iperf is the udp data bitrate, not the ethernet frame size as we want
    framesize = 1514
    headers = 42
    length = framesize - headers
    bitrate = bitrate * length / framesize

    cmd_client = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'sleep 0.5; iperf -c %s -p %d %s -u -l %d -R -b %d -i 1 -t 99999' % (
        os.environ['IP_CLIENT%s' % node],
        server_port,
        tos,
        length,
        bitrate
    )]

    logger.debug(get_log_cmd(cmd_server))
    logger.debug(get_log_cmd(cmd_client))
    if dry_run:
        def stop_test():
            pass

    else:
        pid_server = run_fn(cmd_server)
        pid_client = run_fn(cmd_client)

        processes.add_known_pid(pid_server)
        processes.add_known_pid(pid_client)

        def stop_test():
            processes.kill_pid(pid_client)
            processes.kill_pid(pid_server)

    return stop_test
