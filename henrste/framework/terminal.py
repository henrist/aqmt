"""
This module contains logic for running processes in the terminal.
"""

import os
from plumbum import local, FG
from plumbum.cmd import bash, tmux
import subprocess

from . import logger


def get_shell_cmd(cmd_object):
    """
    Convert a plumbum cmd to a shell expression
    """
    return ' '.join(cmd_object.formulate(10))


def get_log_cmd(cmd, prefix='SHELL: '):
    if not isinstance(cmd, str):
        cmd = get_shell_cmd(cmd)
    return '%s %s' % (prefix, cmd)


class Terminal:
    def __init__(self):
        pass

    def cleanup(self):
        pass

    def run_fg(self, cmd):
        cmd = get_shell_cmd(cmd)
        p = bash['-c', cmd].popen(stdin=None, stdout=None, stderr=None, close_fds=True)

        logger.trace('RUN_FG (PID: %d): %s' % (p.pid, get_log_cmd(cmd, prefix='')))
        return p.pid

    def run_bg(self, cmd):
        cmd = get_shell_cmd(cmd)
        p = bash['-c', cmd].popen(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

        logger.trace('RUN_BG (PID: %d): %s' % (p.pid, get_log_cmd(cmd, prefix='')))
        return p.pid


class Tmux(Terminal):
    def __init__(self):
        super().__init__()
        if 'TMUX' not in os.environ:
            raise Exception("Please run this inside a tmux session")

        self.win_id = tmux['display-message', '-p', '-t', os.environ['TMUX_PANE'], '#{window_id}']().strip()
        self.session_id = tmux['display-message', '-p', '-t', os.environ['TMUX_PANE'], '#{session_id}']().strip()
        self.win_bg_id = None

        tmux['set-window-option', '-t', self.win_id, 'remain-on-exit', 'on']()
        self.cleanup()

    def cleanup(self):
        self.kill_dead_panes()

    def kill_dead_panes(self):
        (tmux['list-panes', '-s', '-F', '#{pane_dead} #{pane_id}', '-t', self.session_id] | local['grep']['^1'] | local['awk']['{print $2}'] | local['xargs']['-rL1', 'tmux', 'kill-pane', '-t']).run(retcode=None)

    @staticmethod
    def get_pane_id(window_id):
        # for some reasons list-panes is not reliable with -t flag
        # so list everything and find from it
        pane_ids = (tmux['list-panes', '-aF', '#{window_id} #{pane_id}'] | local['grep']['^' + window_id + ' '] | local['awk']['{ print $2 }']).run(retcode=None)[1].split()
        return pane_ids[0]

    def run_fg(self, cmd):
        cmd = get_shell_cmd(cmd)
        pane_pid = tmux['split-window', '-dP', '-t', self.get_pane_id(self.win_id), '-F', '#{pane_pid}', cmd]().strip()

        tmux['select-layout', '-t', self.win_id, 'tiled']()

        logger.trace('RUN_FG (TMUX PID: %d): %s' % (pane_pid, get_log_cmd(cmd, prefix='')))
        return int(pane_pid)

    def run_bg(self, cmd):
        cmd = get_shell_cmd(cmd)

        # create the window if needed
        # output in the end should be the new pid of the running command
        # so that we can stop it later
        if not self.have_bg_win():
            res = tmux['new-window', '-adP', '-F', '#{window_id} #{pane_pid}', '-t', self.win_id, cmd]().strip().split()
            self.win_bg_id = res[0]
            pane_pid = res[1]
            tmux['set-window-option', '-t', self.win_bg_id, 'remain-on-exit', 'on'] & FG

        else:
            pane_pid = tmux['split-window', '-dP', '-t', self.get_pane_id(self.win_bg_id), '-F', '#{pane_pid}', cmd]().strip()
            tmux['select-layout', '-t', self.win_bg_id, 'tiled'] & FG

        logger.trace('RUN_BG (TMUX PID: %d): %s' % (pane_pid, get_log_cmd(cmd, prefix='')))
        return int(pane_pid)

    def have_bg_win(self):
        if self.win_bg_id is None:
            return False

        res = (tmux['list-windows', '-aF', '#{window_id}'] | local['grep']['^' + self.win_bg_id + '$']).run(retcode=None)[1].strip()

        return len(res) > 0
