#!/usr/bin/env python
import getpass
import sys, os, optparse
import subprocess

import re

import time

vanilla = """Executable = %s
Universe = vanilla
getenv = true
%s
output = %s
error = %s
arguments = "%s"
log = %s
notification = %s
initialdir = %s
transfer_executable = false
+Research = False
requirements = (Memory > 1000)
request_memory = 2*1024
Queue"""

def which(app):
    p = subprocess.Popen(['which',app], stdout=subprocess.PIPE)
    out = None
    for line in p.stdout:
        out = line.decode(encoding='utf-8').strip()
    return out

def condor_submit(file):
    p = subprocess.Popen(['condor_submit', file])

def create_parents(file):
    p = subprocess.Popen(['mkdir','-p',file])
    p.wait()


def condor_wait():
    while True:
        p = subprocess.Popen(['condor_q', getpass.getuser()], stdout=subprocess.PIPE)
        p.wait()
        result = p.stdout.read().decode(encoding='utf-8')
        jobs_re = re.search('([0-9]+) jobs;', result)
        num_jobs = int(jobs_re.group(1))

        if num_jobs == 0:
            break
        else:
            time.sleep(2)

def run_cmd(args, prefix, name, email, stdin = "", cwd = os.getcwd()):

    # First, make sure the program can be found.
    exe      = args[0]
    exe_path = which(exe)
    if not os.path.exists(exe_path):
        print('Error: the command "%s" could not be found!' % exe)
        sys.exit(-1)
    if stdin and not os.path.exists(stdin):
        sys.stderr.write('ERROR: The stdin file "%s" could not be found' % stdin)
        sys.exit(-127)
    exe = exe_path

    # Create the directory for the prefix, if needed.
    create_parents(prefix)

    # Now, make the commandline back into a string.
    arg_str = ''
    for arg in args[1:]:
        arg_str += '%s ' % arg

    fileprefix = os.path.join(prefix, name)
    # Set up the paths we're going to write.
    cmdpath = fileprefix + ".cmd"
    outpath = fileprefix + ".out"
    errpath = fileprefix + ".err"
    logpath = fileprefix + ".log"

    # Now, write the .cmd file to submit to condor.
    cmdfile = open(cmdpath, 'w')

    if email:
        notification = 'Complete'
    else:
        notification = 'Never'

    if not stdin:
        stdin = '# No stdin given'
    else:
        stdin = 'input = %s' % stdin
    cmdfile.write(vanilla % (exe, stdin, outpath, errpath, arg_str, logpath, notification, cwd))
    cmdfile.close()

    condor_submit(cmdpath)


def usage():
    return '%prog [OPTIONS] COMMAND'

if __name__ == '__main__':

    p = optparse.OptionParser()

    p.add_option('--disable-email', dest='email', action='store_false', help="Don't send an email at job completion.", default=True)


    p.add_option('-i', '--stdin', dest='stdin', help='Supply the following file as stdin')

    p.add_option('-p', '--prefix', dest='prefix', default=os.getcwd(), help="The directory to store the stderr/stdout files.")
    p.add_option('-n', '--name', dest='name', default='condor_job')
    p.add_option('-d', '--cwd', dest='cwd', default=os.getcwd())
    (options, args) = p.parse_args(sys.argv)



    if len(args) < 2:
        p.usage = usage()
        p.print_help()
        sys.exit()

    run_cmd(args[1:], options.prefix, options.name, options.email, stdin = options.stdin, cwd = options.cwd)
