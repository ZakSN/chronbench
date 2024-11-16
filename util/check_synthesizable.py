import subprocess
import sys
import os
import shutil
import argparse
import configparser
import math
import multiprocessing
import time

from tool_automation import VivadoSynthesis
from tool_automation import QuartusSynthesis

sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks
from build_benchmark import ChronbenchBenchmark

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
