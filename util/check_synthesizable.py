import subprocess
import sys
import os
import shutil
import argparse
import configparser
import math
import multiprocessing
import time

sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks
from build_benchmark import ChronbenchBenchmark

class SynthesisTool:
    '''
    A generic synthesis tool class
    '''
    tool_name = 'GENERIC'
    synth_script_name = 'GENERIC_synth_script.tcl'
    success_msg = 'GENERIC SUCCESS'
    logfile_name = 'path_to_synth_log'

    def __init__(self, proj_dir, cbb):
        self.proj_dir = proj_dir
        self.cbb = cbb

    def run_synthesis(self):
        self._build_synth_script()
        self._write_synth_script()
        self._run_tool()
        self._report_result()

    def _build_synth_script(self):
        pass

    def _write_synth_script(self):
        self.synth_script_path = os.path.join(self.proj_dir, self.synth_script_name)
        with open(self.synth_script_path, 'w') as script:
            for line in self.synth_script:
                script.write(line+'\n')

    def _run_tool(self):
        start = time.time()
        self._run_tool_wrapped()
        stop = time.time()
        self.elapsed = stop - start

    def _report_result(self):
        '''
        Check to see if synthesis was successful.
        '''
        # read the log to see if synthesis was successful
        logfile = os.path.join(self.proj_dir, self.logfile_name)
        with open(logfile, 'r') as log:
            synth_result = log.readlines()

        success = False
        for line in synth_result:
            if self.success_msg in line:
                success = True

        # print a message to the terminal and write a PASS/FAIL file
        if success:
            r = 'PASS'
        else:
            r = 'FAIL'
        with open(os.path.join(self.proj_dir, self.tool_name + '_synth.'+r), 'w') as f:
            f.write(r+'\n')
            f.write(str(self.elapsed)+'\n')
        print(self.proj_dir+': '+r+", "+str(self.elapsed))

class QuartusSynthesis(SynthesisTool):
    '''
    Use Quartus to synthesize a commit level synthesis project.

    Assumes Quartus executables are on the system path
    '''
    tool_name = 'quartus'
    synth_script_name = 'quartus_synth_script.tcl'
    success_msg = 'Info: Successfully synthesized'
    logfile_name = os.path.join('output_files', 'autoqpf.syn.rpt')

    def _build_synth_script(self):
        '''
        Create a tcl script to run Quartus Synthesis
        '''
        # check for Quartus specific hacks
        try:
            quartus_extra_commands = self.cbb.benchmark['quartus-extra-commands'].split('\n')
        except:
            quartus_extra_commands = ''

        # get the benchmark top module
        top = self.cbb.benchmark['top']

        # create the synth script
        self.synth_script = [
            'project_new autoqpf -overwrite',
            'set_global_assignment -name TOP_LEVEL_ENTITY '+top,
            'set_global_assignment -name DEVICE 1SG085HN1F43E1VG',
            'set_global_assignment -name FAMILY "Stratix 10"',
            'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
            *quartus_extra_commands,
            'set sources [glob src/*]',
            'foreach src $sources {',
            '    set ext [file extension $src]',
            '    switch $ext {',
            '        .v -',
            '        .vh {set filetype VERILOG_FILE}',
            '        .sv -',
            '        .svh {set filetype SYSTEMVERILOG_FILE}',
            '        .vdh {set filetype VHDL_FILE}',
            '    }',
            '    set_global_assignment -name $filetype $src',
            '}',
            'project_close',
        ]

    def _run_tool_wrapped(self):
        '''
        Use quaruts to build a project from the source files and then
        synthesize that project. Assumes Quartus executables are on the path
        '''
        subprocess.run(['quartus_sh', '-t', 'quartus_synth_script.tcl'], cwd=self.proj_dir, capture_output=True)
        subprocess.run(['quartus_syn', 'autoqpf'], cwd=self.proj_dir, capture_output=True)

class VivadoSynthesis(SynthesisTool):
    '''
    Use Vivado to synthesize a commit level synthesis project.

    Assumes Vivado executables are on the system path
    '''
    tool_name = 'vivado'
    synth_script_name = 'vivado_synth_script.tcl'
    success_msg = 'synth_design completed successfully'
    logfile_name = 'vivado.log'

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
            *vivado_extra_commands,
            'add_files src',
            'set synth_args {'+vivado_synth_args+'}',
            'catch {synth_design -top '+top+' {*}$synth_args}',
            'exit',
        ]

    def _run_tool_wrapped(self):
        '''
        Run Vivado in headless mode to execute the synthscript in the commit
        level project directory. Assume Vivado is on the path.
        '''
        subprocess.run(['vivado', '-mode', 'tcl', '-source', self.synth_script_name], cwd=self.proj_dir, capture_output=True)

class CheckSynthesizable:
    '''
    Create commit level synthesis projects for each commit in the range
    HEAD..HEAD~<depth> of the provided benchmark, and then run the provided
    synthesis tool on each.
    '''
    def __init__(self, benchmark, depth, tool, workers=1):
        self.cbb = ChronbenchBenchmark(benchmark, None)
        self.depth = depth
        self.synth_dir = os.path.join('util', self.cbb.name+'_'+tool.tool_name+'_synth_projects')
        self.tool = tool
        self.workers = workers

    def synthesize_snapshots(self):
        '''
        Create a synthesis project for each commit in the range
        HEAD..HEAD~<depth>. Assign projects to workers as uniformly as possible,
        and then run synthesis in each.
        '''
        # get a list of all the projects to synthesize
        projects = self._setup_synthesis_projects()

        # distribute projects amongst workers to form jobs
        jobs = [ [] for _ in range(self.workers)]
        while len(projects) > 0:
            for w in range(self.workers):
                try:
                    jobs[w].append(projects.pop())
                except:
                    pass

        # launch a worker for each job
        for j in jobs:
            proc = multiprocessing.Process(target=CheckSynthesizable._launch_worker, args=(self, j))
            proc.start()

    def _launch_worker(self, job):
        '''
        Run synthesis for all projects in a job
        '''
        for project in job:
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

def main():
    os.chdir('..')

    parser = argparse.ArgumentParser(
        prog='check_synthesizable.py',
        description='attempt to synthesize each snapshot of a time series benchmark'
    )

    benchmarks = get_available_benchmarks('benchmarks')
    benchmark_names = benchmarks.keys()

    tools = {
        'vivado':  VivadoSynthesis,
        'quartus': QuartusSynthesis,
    }

    parser.add_argument('tool', choices=tools.keys(), help='synthesis tool to use')
    parser.add_argument('benchmark_name', choices=benchmark_names, help='synthesize the named benchmark')
    parser.add_argument('depth', type=int, help='number of predecessor commits to try synthesizing')
    parser.add_argument('-j', type=int, help='max number of synthesis jobs to run', default=1)

    args = parser.parse_args()

    benchmark = benchmarks[args.benchmark_name]
    depth = args.depth

    cs = CheckSynthesizable(benchmark, depth, tools[args.tool], args.j)
    cs.synthesize_snapshots()

if __name__ == '__main__':
    main()
