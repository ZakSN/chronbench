import subprocess
import sys
import os
import shutil
import argparse
import configparser
import math

sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_benchmarks
from build_benchmark import read_benchmark_config

def run_vivado_synth(name, top, logdir, prefix, sha, vivado_extra_commands, vivado_synth_args):
    '''
    Synthesize the HDL located in name, with the top module as top, using
    Vivado.

    Assumes vivado is on the path, and uses `vivado_synth.tcl` to run
    synthesis.

    returns True if synthesis was successful
    '''

    # This message should turn up in the log to indicate successful synthesis
    success_msg = 'synth_design completed successfully'

    # The directories and files we expect Vivado to produce
    projdir = 'autosynthxpr'
    journalfile = 'vivado.jou'
    logfile = 'vivado.log'
    synth_script = 'vivado_synth.tcl'

    # annoyingly vivado can't exec tcl from the command line, so we write a
    # temporary script
    with open(synth_script, 'w') as f:
        f.writelines(
            '''
            set outputdir autosynthxpr
            set project autosynth
            set partnumber xcvu3p-ffvc1517-3-e

            file mkdir $outputdir

            create_project -part $partnumber $project $outputdir

            add_files [lindex $argv 0]
            '''
            +vivado_extra_commands+
            '''
            set synth_args {'''+vivado_synth_args+'''}

            catch {synth_design -top [lindex $argv 1] {*}$synth_args}

            exit
            ''')

    # run vivado, and surpress the output
    subprocess.run(['vivado', '-mode', 'tcl', '-source', synth_script, '-tclargs', name, top], capture_output=True)

    # ensure that vivado ran properly and bailout other wise
    xpr_exists = os.path.isdir(projdir)
    journal_exists = os.path.isfile(journalfile)
    log_exists = os.path.isfile(logfile)
    if not (xpr_exists and journal_exists and log_exists):
        print("FAILED: Seems like Vivado did not run.")
        exit()

    # read the log to see if synthesis was successful
    with open(logfile, 'r') as vlog:
        synth_result = vlog.readlines()

    success = False
    for line in synth_result:
        if success_msg in line:
            success = True

    # clean up vivado project
    shutil.rmtree(projdir)
    os.remove(journalfile)
    os.remove(synth_script)

    # rename the log file with the result and sha
    os.rename(logfile, os.path.join(logdir, prefix + "_" + sha + "_" + str(success) + ".log"))

    return success

def get_sha(name):
    '''
    Get the SHA of HEAD in the repo `name`

    returns the SHA as a string
    '''
    sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=name, capture_output=True)
    sha = sha.stdout.decode('utf8').replace('\n','')
    return sha

def checkout_sha(repo, sha):
    msg = subprocess.run(['git', 'checkout', sha], cwd=repo, capture_output=True)
    msg = msg.stderr.decode('utf8').replace('\n','n')
    return msg

def step_back_one_commit(name):
    '''
    Step HEAD back one commit in the repo `name`

    returns false if end of history was detected, true otherwise
    '''
    # the message we expect if we hit the oldest commit
    end_of_hist = "error: pathspec 'HEAD~1' did not match any file(s) known to git."

    # attempt to step back one commit
    msg = checkout_sha(name, 'HEAD~1')

    # check to see if we hit oldest commit
    if end_of_hist in msg:
        return False
    else:
        return True

def create_log_dir(logdir):
    '''
    If it doesn't all ready exist create a directory to preserve synthesis logs
    '''
    logdir_exists = os.path.isdir(logdir)
    if not logdir_exists:
        os.makedirs(logdir)

def main():
    parser = argparse.ArgumentParser(
        prog='check_synthesizable.py',
        description='attempt to synthesize each snapshot of a time series benchmark'
    )

    benchmarks = get_benchmarks(os.path.join('..','benchmarks'))
    benchmark_names = benchmarks.keys()

    parser.add_argument('benchmark_name', choices=benchmark_names, help='synthesize the named benchmark')
    parser.add_argument('depth', type=int, help='number of predecessor commit to try synthesizing')

    args = parser.parse_args()

    benchmark = read_benchmark_config(benchmarks[args.benchmark_name])

    bpath = os.path.join('..',args.benchmark_name)
    top = benchmark[args.benchmark_name]['top']
    start_sha = benchmark[args.benchmark_name]['branch']

    #populate optional fields
    try:
        vivado_extra_commands = benchmark[args.benchmark_name]['vivado-extra-commands']
    except:
        vivado_extra_commands = ''
    try:
        vivado_synth_args = benchmark[args.benchmark_name]['vivado-synth-args']
    except:
        vivado_synth_args = ''

    commit_depth = args.depth

    # make sure we're starting at the right spot
    checkout_sha(bpath, start_sha)

    logdir = "synth_logs"
    create_log_dir(logdir)
    prefix_digits = math.ceil(math.log(commit_depth, 10))

    for prefix in range(commit_depth):
        sha = get_sha(bpath)
        prefix_str = "{:0"+str(prefix_digits)+"d}"
        prefix_str = prefix_str.format(prefix)
        synth_result = run_vivado_synth(bpath, top, logdir, prefix_str, sha, vivado_extra_commands, vivado_synth_args)

        if synth_result:
            print(sha + " Synthesizable")
        else:
            print(sha + " Unsynthesizable")

        stepped = step_back_one_commit(bpath)
        if not stepped:
            print("QUITTING: reached end of history")
            exit()

if __name__ == '__main__':
    main()
