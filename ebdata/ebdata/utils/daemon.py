# The following is from http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
# with slight formatting changes. The author of the code there has placed it in the public domain.

import atexit
import sys
import os
import time
from signal import SIGTERM
from optparse import OptionParser

class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def run_from_command_line(self, argv):
        """
        Given sys.argv, parses the command-line arguments and calls the
        appropriate method, failing appropriately in case of problems.
        """
        usage = "usage: %prog [options] start|stop|restart"
        parser = OptionParser(usage=usage)
        parser.add_option("-D", "--debug", help="run in debugging mode (run in the foreground)",
                          action="store_true", dest="debugging", default=False)
        (options, args) = parser.parse_args(argv)
        if len(args) == 1:
            if args[0] == 'start':
                self.start(options.debugging)
            elif args[0] == 'stop':
                self.stop()
            elif args[0] == 'restart':
                self.restart()
            else:
                parser.error("unknown command")
                sys.exit(2)
            sys.exit(0)
        else:
            parser.error("invalid command")
            sys.exit(2)

    def daemonize(self):
        """
        Do the UNIX double-fork magic. See Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        """
        try:
            pid = os.fork()
            if pid > 0:
                # Exit the first parent.
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from the parent environment.
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # Do the second fork.
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from the second parent.
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Redirect standard file descriptors. Because the daemon has no
        # controlling terminal, we want to avoid side effects from reading and
        # writing to/from the standard file descriptors.
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        # Use os.dup2() with the fileno() instead of assigning directly to
        # sys.stdout because the former will also affect any C-level sys.stdout
        # calls.
        os.dup2(si.fileno(), sys.stdin.fileno())  # Essentially: sys.stdin = si
        os.dup2(so.fileno(), sys.stdout.fileno()) # Essentially: sys.stdout = so
        os.dup2(se.fileno(), sys.stderr.fileno()) # Essentially: sys.stderr = se

        # Write the pidfile.
        atexit.register(self.delpid)
        pid = str(os.getpid())
        open(self.pidfile, 'w+').write("%s\n" % pid)

    def get_pid_from_file(self):
        "Returns the pid value from the file."
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        return pid

    def delpid(self):
        os.remove(self.pidfile)

    def start(self, debug=False):
        """
        Starts the daemon.
        """
        # Check for a pidfile to see whether the daemon is already running.
        if self.get_pid_from_file():
            sys.stderr.write("pidfile %s already exists. Is the daemon already running?\n" % self.pidfile)
            sys.exit(1)

        # Don't detach from foreground if debugging.
        if not debug:
            self.daemonize()
        # Start the daemon.
        self.run()

    def stop(self):
        """
        Stops the daemon.
        """
        # Get the pid from the pidfile.
        pid = self.get_pid_from_file()

        if not pid:
            sys.stderr.write("pidfile %s does not exist. Is the daemon not running?\n" % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process.
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restarts the daemon.
        """
        self.stop()
        self.start()

    def run(self):
        """
        The daemon's logic.

        Subclasses should override this method.
        """
        raise NotImplementedError()
