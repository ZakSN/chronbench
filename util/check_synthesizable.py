import subprocess
import sys
import os
import shutil
import argparse
import configparser
import math

sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks
from build_benchmark import ChronbenchBenchmark

class SynthesisTool:
    '''
    A generic synthesis tool class
    '''
    def __init__(self, proj_dir, cbb):
        self.proj_dir = proj_dir
        self.cbb = cbb
        pass

    def run_synthesis(self):
        print("Running Synthesis on: "+self.proj_dir)

class VivadoSynthesis(SynthesisTool):
    '''
    Use vivado to synthesis a commit level synthesis project
    '''

    def run_synthesis(self):
        print("Vivado Synthesis on: "+self.proj_dir)
        self._build_synth_script()
        self._write_synth_script()

    def _build_synth_script(self):
        '''
        Create a tcl script to run Vivado synthesis
        '''
        # Check for any Vivado specific hacks
        try:
            vivado_extra_commands = self.cbb.benchmark['vivado-extra-commands'].split('\n')
        except:
            vivado_extra_commands = ''
        try:
            vivado_synth_args = self.cbb.benchmark['vivado-synth-args']
        except:
            vivado_synth_args = ''

        # get the benchmark top module
        top = self.cbb.benchmark['top']

        # create the synth script
        self.synth_script = [
            'set outputdir autosynthxpr',
            'set project autosynth',
            'set partnumber xcvu3p-ffvc1517-3-e',
            'file mkdir $outputdir',
            'create_project -part $partnumber $project $outputdir',
            'add_files src',
            *vivado_extra_commands,
            'set synth_args {'+vivado_synth_args+'}',
            'catch {synth_design -top '+top+' {*}$synth_args}',
            'exit',
        ]

    def _write_synth_script(self):
        with open(os.path.join(self.proj_dir, 'vivado_synth_script.tcl'), 'w') as script:
            for line in self.synth_script:
                script.write(line+'\n')


class CheckSynthesizable:
    '''
    Create commit level synthesis projects for each commit in the range
    HEAD..HEAD~<depth> of the provided benchmark, and then run the provided
    synthesis tool on each.
    '''
    def __init__(self, benchmark, depth, tool):
        self.cbb = ChronbenchBenchmark(benchmark, None)
        self.depth = depth
        self.synth_dir = os.path.join('util', self.cbb.name + '_synth_projects')
        self.tool = tool

    def synthesize_snapshots(self):
        '''
        Create a synthesis project for each commit in the range
        HEAD..HEAD~<depth>, and run synthesis in each.
        '''
        projects = self._setup_synthesis_projects()
        for project in projects:
            project.run_synthesis()

    def _setup_synthesis_projects(self):
            '''
            Create a directory structure suitable for synthesizing many benchmark
            commits in parallel.

            Finished directory structure looks like this:
            <benchmark>_synth_projects/
                00_<sha>/
                    src/
                        <all source files from <benchmark>@<sha>>
                01_<sha>/
                    src/
                        <all source files from <benchmark>@<sha>>
                ...
                depth_<sha>/
                    src/
                        <all source files from <benchmark>@<sha>>
            '''
            # create the main directory
            self._create_experiment_dir()

            # get a list of all available commits in the current benchmark
            self.cbb._run_cmd('git checkout '+self.cbb.branch)
            available_commits = self.cbb._run_cmd('git log --format=format:%H')
 
            # figure out the number of commits to synthesize
            depth = min(self.depth, int(self.cbb.depth))

            # figure out how many digits to use in the prefix
            prefix_digits = math.ceil(math.log(depth, 10))
            prefix_str = "{:0"+str(prefix_digits)+"d}"

            # starting at the most recent commit set up <depth> projects
            projects = []
            for cidx in range(depth):
                prefix = prefix_str.format(cidx)
                commit_dir = self._initialize_commit_dir(prefix, available_commits[cidx])
                projects.append(self.tool(commit_dir, self.cbb))

            return projects

    def _create_experiment_dir(self):
        '''
        Create a directory to hold commit-level synthesis projects.
        '''
        if not os.path.isdir(self.synth_dir):
            os.makedirs(self.synth_dir)
        else:
            print("QUITTING: A synthesis project for this benchmark already exists")
            exit()

    def _initialize_commit_dir(self, prefix, sha):
        '''
        Create a commit-level project directory, in the experiment directory.
        Then checkout the benchmark at the corresponding commit and copy all
        the sources into a `src` directory in the commit-level directory.

        Returns the path to the commit-level directory
        '''
        commit_dir = os.path.join(self.synth_dir, prefix+'_'+sha)
        os.makedirs(commit_dir)

        self.cbb._run_cmd('git checkout '+sha)
        shutil.copytree(self.cbb.name, os.path.join(commit_dir, 'src'), ignore=shutil.ignore_patterns('.git*'))

        return commit_dir

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

def main1():
    os.chdir('..')

    benchmarks = get_available_benchmarks(os.path.join('benchmarks'))

    benchmark = benchmarks['cva5']
    depth = 2

    cs = CheckSynthesizable(benchmark, depth, VivadoSynthesis)
    cs.synthesize_snapshots()

def main():
    parser = argparse.ArgumentParser(
        prog='check_synthesizable.py',
        description='attempt to synthesize each snapshot of a time series benchmark'
    )

    benchmarks = get_available_benchmarks(os.path.join('..','benchmarks'))
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
    main1()
