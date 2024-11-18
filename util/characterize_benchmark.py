import os
import sys
import argparse
import math
import shutil
import multiprocessing

from tool_automation import Vivado
from tool_automation import Quartus

sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks
from build_benchmark import ChronbenchBenchmark

class SetupCharacterizationProjects:
    '''
    Create a directory structure that flattens the time dimension of a
    Chronbench benchmark.
    '''
    def __init__(self, benchmark, tool):
        self.cbb = ChronbenchBenchmark(benchmark, None)
        self.char_dir = os.path.join('util', self.cbb.name+'_'+tool+'_char_projects')

    def build_directory_structure(self):
            '''
            Create a directory structure suitable for building many benchmark
            commits in parallel.

            Finished directory structure looks like this:
            <benchmark>_char_projects/
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

            Returns a tuple of the current benchmark and a list of all of the
            commit level directories.
            '''
            # create the main directory
            try:
                self._create_char_dir()
            except FileExistsError:
                projects = self._enumerate_existing_projects()
                print('Found '+str(len(projects))+' commit directories')
            else:
                # get a list of all available commits in the current benchmark
                self.cbb._run_cmd('git checkout '+self.cbb.branch)
                available_commits = self.cbb._run_cmd('git log --format=format:%H')

                # figure out the number of commits to synthesize
                depth = len(available_commits)
                print('Building '+str(depth)+' commit directories')

                # figure out how many digits to use in the prefix
                prefix_digits = math.ceil(math.log(depth, 10))
                prefix_str = "{:0"+str(prefix_digits)+"d}"

                # starting at the most recent commit set up <depth> projects
                projects = []
                for cidx in range(depth):
                    prefix = prefix_str.format(cidx)
                    commit_dir = self._initialize_commit_dir(prefix, available_commits[cidx])
                    projects.append(commit_dir)
            finally:
                self.char_proj = (self.cbb, projects)
                return self.char_proj

    def _create_char_dir(self):
        '''
        Create a directory to hold commit-level characterization projects.
        '''
        if not os.path.isdir(self.char_dir):
            os.makedirs(self.char_dir)
        else:
            raise FileExistsError

    def _initialize_commit_dir(self, prefix, sha):
        '''
        Create a commit-level project directory, in the experiment directory.
        Then checkout the benchmark at the corresponding commit and copy all
        the sources into a `src` directory in the commit-level directory.

        Returns the path to the commit-level directory
        '''
        commit_dir = os.path.join(self.char_dir, prefix+'_'+sha)
        os.makedirs(commit_dir)

        self.cbb._run_cmd('git checkout '+sha)
        shutil.copytree(self.cbb.name, os.path.join(commit_dir, 'src'), ignore=shutil.ignore_patterns('.git*'))

        return commit_dir

    def _enumerate_existing_projects(self):
        '''
        Get a list of all of the subdirectories in the char project directory.
        Assumes directory structure is as default
        '''
        projects = []
        for f in os.scandir(self.char_dir):
            if os.path.isdir(f):
                projects.append(f.path)
        return projects

class RunFPGATool:
    '''
    Run Synthesis and/or PnR on a characterization project
    '''
    def __init__(self, tool, char_proj, workers=1):
        self.tool = tool
        self.cbb = char_proj[0]
        self.projects = char_proj[1]
        self.workers = workers
        self._distribute_work()

    def _distribute_work(self):
        '''
        Create a job queue for each worker
        '''
        projects = []
        for p in self.projects:
            projects.append(self.tool(p, self.cbb))

        # distribute projects amongst workers to form jobs
        jobs = [ [] for _ in range(self.workers)]
        while len(projects) > 0:
            for w in range(self.workers):
                try:
                    jobs[w].append(projects.pop())
                except:
                    pass
        self.jobs = jobs

    def _start_workers(self, worker):
        '''
        Launch a worker for each job
        '''
        procs = []
        for j in self.jobs:
            proc = multiprocessing.Process(target=worker, args=(self, j))
            proc.start()
            procs.append(proc)
        return procs

    def synthesis(self):
        '''
        Start synthesis workers
        '''
        print('Starting Synthesis')
        procs = self._start_workers(RunFPGATool._synth_worker)
        for p in procs:
            p.join()

    def _synth_worker(self, job):
        '''
        Run synthesis for all projects in a job
        '''
        for project in job:
            project.run_synthesis()

    def pnr(self):
        '''
        Start place and route workers
        '''
        print('Starting Place and Route')
        procs = self._start_workers(RunFPGATool._pnr_worker)
        for p in procs:
            p.join()

    def _pnr_worker(self, job):
        '''
        Run place and route for all projects in a job
        '''
        for project in job:
            project.run_pnr()

def main():
    os.chdir('..')

    parser = argparse.ArgumentParser(
        prog='characterize_benchmark.py',
        description='characterize a time series benchmark'
    )

    benchmarks = get_available_benchmarks('benchmarks')
    benchmark_names = benchmarks.keys()

    tools = {
        'vivado':  Vivado,
        'quartus': Quartus,
    }

    steps = ['setup', 'synth', 'pnr']

    parser.add_argument('tool', choices=tools.keys(), help='FPGA tool to use')
    parser.add_argument('step', choices=steps, help='FPGA flow steps to use. steps automatically run dependancies.')
    parser.add_argument('benchmark_name', choices=benchmark_names, help='benchmark to operate on')
    parser.add_argument('-j', type=int, help='max number of synthesis jobs to run', default=1)

    args = parser.parse_args()

    benchmark = benchmarks[args.benchmark_name]

    scp = SetupCharacterizationProjects(benchmark, args.tool)
    char_proj = scp.build_directory_structure()
    if args.step == 'synth' or args.step =='pnr':
        RFT = RunFPGATool(tools[args.tool], char_proj, args.j)
        RFT.synthesis()
        if args.step == 'pnr':
            RFT.pnr()

if __name__ == '__main__':
    main()
