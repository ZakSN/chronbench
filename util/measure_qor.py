import os
import sys
import multiprocessing

from tool_automation import VivadoSynthesis

sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks
from build_benchmark import ChronbenchBenchmark

class MeasureQoR:
    '''
    Measure the Quality of Results (Area and Fmax) on all synthesized commits
    in a benchmark. Assumes check_synthesizable.py has all ready been run on
    the appropriate benchmark to produce the required synthesis projects.
    '''
    def __init__(self, benchmark, tool, workers=1):
        self.cbb = ChronbenchBenchmark(benchmark, None)
        self.synth_dir = os.path.join('util', self.cbb.name+'_'+tool.tool_name+'_synth_projects')
        self.tool = tool
        self.workers = workers

    def do_measurement(self):
        '''
        Setup and launch tool runs required to measure Area and Fmax
        '''
        # Figure out how many systhesis projects are available for the given
        # benchmark
        projects = self._enumerate_synth_projects()

        # Distribute the projects amongst available workers
        jobs = [ [] for _ in range(self.workers)]
        while len(projects) > 0:
            for w in range(self.workers):
                try:
                    jobs[w].append(projects.pop())
                except:
                    pass

        # launch the workers
        for j in jobs:
            proc = multiprocessing.Process(target=MeasureQoR._launch_worker, args=(self, j))
            proc.start()

    def _enumerate_synth_projects(self):
        '''
        Get a list of all of the subdirectories in the synth project directory.
        Assumes directory structure has not been changed since running
        CheckSynthesis
        '''
        projects = []
        for f in os.scandir(self.synth_dir):
            if os.path.isdir(f):
                projects.append(os.path.join(self.synth_dir, f))
        return projects

    def _launch_worker(self, job):
        for project in job:
            print(project)

def main():
    os.chdir('..')

    benchmarks = get_available_benchmarks('benchmarks')

    mqor = MeasureQoR(benchmarks['jt12'], VivadoSynthesis, 4)
    mqor.do_measurement()

if __name__ == '__main__':
    main()
