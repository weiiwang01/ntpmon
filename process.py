#!/usr/bin/env python3
#
# Copyright:    (c) 2016 Paul D. Gear
# License:      GPLv3 <http://www.gnu.org/licenses/gpl.html>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#

import subprocess
import sys
import time

import psutil

from peers import NTPPeers
from trace import NTPTrace


_progs = {
    'peers': 'ntpq -pn',
    'trace': 'ntptrace -n',
    'vars': 'ntpq -nc readvar',
}


def execute(prog, timeout=30, debug=False, errfatal=False):
    """
    Execute a predefined external command.
    """
    if prog not in _progs:
        return None
    failmessage = '%s produced no output.  Please check that an NTP server is installed and running.'

    output = None
    cmd = _progs[prog].split()
    try:
        output = subprocess.check_output(
            cmd,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout,
            universal_newlines=True,
        )
    except subprocess.CalledProcessError as cpe:
        # FIXME: should be a metric rather than fatal error
        if errfatal:
            fatal('%s returned %d: %s' % (
                " ".join(cpe.cmd),
                cpe.returncode,
                cpe.stderr,
            ))
    except subprocess.TimeoutExpired as te:
        if debug:
            print(te)
        output = te.output

    if output is None or output == "":
        if errfatal:
            # FIXME: should be a metric rather than fatal error
            fatal(failmessage % _progs[prog])
        else:
            return []
    else:
        if debug:
            print(output)
        return output.split('\n')


def fatal(msg):
    print('UNKNOWN: ' + msg)
    sys.exit(3)


def ntpchecks(checks, debug):
    """
    Run all of the checks required by the argument list
    and return the resulting objects in a hash.
    """
    objs = {}

    for check in checks:
        if ((debug or check in ['offset', 'peers', 'reach', 'sync'])
                and 'peers' not in objs):
            objs['peers'] = NTPPeers(execute('peers', debug=debug))

        if ((debug or check == 'trace')
                and 'trace' not in objs):
            objs['trace'] = NTPTrace(execute('trace', debug=debug))

        if ((debug or check == 'trace') and trace is None):
            trace = NTPTrace(execute('trace', debug=debug))

        if ((debug or check == 'proc')
                and 'proc' not in objs):
            objs['proc'] = NTPProcess()

    return objs


class NTPProcess(object):

    def __init__(self, names=None):
        """Look for ntpd or xntpd in the process table and save its process object."""
        if names is None:
            self.names = ["ntpd", "xntpd"]
        else:
            self.names = names
        # Check for old psutil per http://grodola.blogspot.com.au/2014/01/psutil-20-porting.html
        self.PSUTIL2 = psutil.version_info >= (2, 0)

    def getprocess(self):
        """
        Search the process table for a matching process name
        """
        for proc in psutil.process_iter():
            try:
                name = proc.name() if self.PSUTIL2 else proc.name
                if name in self.names:
                    self.name = name
                    return proc
            except psutil.Error:
                pass
        return None

    def getruntime(self):
        """
        Return the length of time in seconds that the process has been running.
        If ntpd is not running or any error occurs, return -1.
        """
        proc = self.getprocess()
        if proc is None:
            return -1
        try:
            now = time.time()
            create_time = proc.create_time() if self.PSUTIL2 else proc.create_time
            start = int(create_time)
            return now - start
        except psutil.Error:
            return -1

    def getmetrics(self):
        return {'runtime': self.getruntime()}


def main():
    import pprint
    pprint.pprint(NTPProcess().getmetrics())


if __name__ == "__main__":
    main()
