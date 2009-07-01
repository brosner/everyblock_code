from ebdata.utils.daemon import Daemon
import datetime
import os
import sys
import time

class EveryMinuteDaemon(Daemon):
    """
    A daemon that calls handle_time() every minute.
    """
    def run(self):
        while 1:
            # Calculate the next minute. We don't care about handling the
            # current minute, because if we did that, it would be handled
            # twice if this program were stopped and restarted during that
            # minute.
            next_minute = datetime.datetime.now() + datetime.timedelta(minutes=1)
            next_minute = next_minute.replace(second=0, microsecond=0)

            # Sleep until the next minute. Add 5 seconds to the sleep time to
            # avoid edge cases and off-by-one errors. Messy but effective.
            sleep_delta = next_minute - datetime.datetime.now()
            time.sleep(sleep_delta.seconds + 5)

            # Call the hook.
            self.handle_time(next_minute)

    def handle_time(self, timestamp):
        pass

class EveryTwoSecondsDaemon(Daemon):
    """
    A daemon that calls handle_time() every two seconds.

    This is useful for debugging -- just replace EveryMinuteDaemon with
    EveryTwoSecondsDaemon in your subclass.
    """
    def run(self):
        while 1:
            self.handle_time(datetime.datetime.now())
            time.sleep(2)

    def handle_time(self, timestamp):
        pass

class UpdaterDaemon(EveryMinuteDaemon):
    def __init__(self, config, *args, **kwargs):
        super(UpdaterDaemon, self).__init__(*args, **kwargs)
        self.config = config

    def handle_time(self, timestamp):
        # Get the tasks for the given timestamp, and run any that need to be
        # run. Reload the config to take into account any changes that might
        # have been made.
        reload(self.config)
        for check, func, kwargs, env in self.config.TASKS:
            if check(timestamp):
                # Fork a child process and grandchild process, and kill the
                # child process immediately so that it doesn't block.
                # For more on this technique, see the final paragraph at
                # http://www.faqs.org/faqs/unix-faq/faq/part3/section-13.html
                try:
                    pid = os.fork()
                except OSError, e:
                    sys.stderr.write("fork failed: %d (%s)\n" % (e.errno, e.strerror))
                    os._exit(1)
                if pid == 0: # child
                    try:
                        pid2 = os.fork()
                    except OSError, e:
                        sys.stderr.write("inner fork failed: %d (%s)\n" % (e.errno, e.strerror))
                        os._exit(1)
                    if pid2 == 0: # child
                        os.environ.update(env)
                        from django.conf import settings

                        # Log the function call and PID.
                        sys.stdout.write('%s\t%s\t%r\t%s\n' % (datetime.datetime.now(), func.func_name, kwargs, os.getpid()))
                        sys.stdout.flush()

                        try:
                            func(**kwargs)
                        except Exception, e:
                            from django.core.mail import mail_admins
                            import traceback
                            traceback_string = '\n'.join(traceback.format_exception(*sys.exc_info()))
                            sys.stderr.write("ERROR AT %s\n" % datetime.datetime.now())
                            sys.stderr.write(traceback_string)
                            sys.stderr.write("\n========================================\n")
                            subject = '%s %s' % (func.func_name, str(kwargs).replace('\n', ' '))
                            try:
                                mail_admins(subject, traceback_string)
                            except Exception, e:
                                sys.stderr.write("Got error mailing admins: %s\n" % e)
                            # Don't call sys.exit() for this,
                            # because we're in a child process.
                            os._exit(1)
                        sys.stdout.flush()
                    os._exit(0)
                else: # parent
                    os.waitpid(pid, 0)

if __name__ == "__main__":
    from ebdata.retrieval.updaterdaemon import config
    daemon = UpdaterDaemon(config, '/tmp/updaterdaemon.pid',
        stdout='/tmp/updaterdaemon.log',
        stderr='/tmp/updaterdaemon.err')
    daemon.run_from_command_line(sys.argv[1:])
