"""
This module handles process related stuff such as keeping track
of special processes we want to kill later and utility methods
for handling running processes.
"""

import errno
import time
import os
import signal

from . import logger

is_exiting = False
known_pids = []


def kill_known_pids():
    global known_pids
    for pid in known_pids:
        kill_pid(pid)

    known_pids = []


def add_known_pid(pid):
    global known_pids
    known_pids.append(pid)


def kill_pid(pid):
    try:
        os.kill(pid, signal.SIGTERM)
        logger.trace('Sent SIGTERM to PID %d' % pid)
    except ProcessLookupError:
        pass


def is_running(pid):
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            return False
    return True


def waitpid(pid):
    # due to some issues when running child process vs tmux this is a bit more complex
    # first use os.waitpid in case this is a child of current process
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass

    while is_running(pid):
        time.sleep(0.3)
