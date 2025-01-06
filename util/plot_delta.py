import matplotlib.pyplot as plt
import matplotlib
import sys
import os
import numpy as np

from plot_qor import collect_tmin_data
from plot_qor import collect_util_data
from characterize_benchmark import SetupCharacterizationProjects
sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks

def get_src_stats(cbb):
    '''
    Count the number of lines impacted by each commit in ChronBench Benchmark
    `cbb'
    '''
    cbb._run_cmd('git checkout '+cbb.branch)
    raw_src_stats = cbb._run_cmd('git log --shortstat --format=format:%at')
    src_stats = []
    for line in raw_src_stats:
        try:
            int(line)
        except ValueError:
            if len(line) != 0:
                net = 0
                for change in line.split(',')[1:]:
                    if '+' in change:
                        net = net + int(change.split()[0])
                    else:
                        net = net + int(change.split()[0])
                src_stats.append(net)
    return src_stats

def repackage_data(data):
    '''
    repackage the raw src, utilization, and timing statistics into a coherent
    dictionary:
        key: benchmark name
        value: [<delta_sloc, clbs, fmid, frange>...]
    '''
    repack_data = dict.fromkeys(data)
    for benchmark_name, raw in data.items():
        commits = []
        for cidx in range(len(raw[0])):
            delta_sloc = raw[0][cidx]
            # util
            clbs = raw[1][1][cidx]
            # tmin
            fmid = raw[2][1][cidx]
            frange = raw[2][2][cidx]
            commits.append((delta_sloc, clbs, fmid, frange))
        repack_data[benchmark_name] = commits
    return repack_data

def reduce_data(data):
    '''
    reduce the repackaged data to compute delta clbs, delta fmid, and delta frange
    we leave delta_sloc as is reported by git. Consider the delta_sloc in the
    root commit to be 0, since this commit simply adds all of the files at the
    beginning of the WoI
    '''
    reduced_data = dict.fromkeys(data)
    for benchmark_name, commits in data.items():
        deltas = []
        for cidx in range(len(commits)-1):
            delta_sloc = commits[cidx][0]
            delta_clbs = abs(commits[cidx][1] - commits[cidx+1][1])
            delta_fmid = abs(commits[cidx][2] - commits[cidx+1][2])
            delta_frange = abs(commits[cidx][3] - commits[cidx+1][3])
            deltas.append((delta_sloc, delta_clbs, delta_fmid, delta_frange))
        reduced_data[benchmark_name] = deltas
    return reduced_data

def plot_sloc_vs_hw(dsloc, dhw):
    plt.scatter(dsloc, dhw, marker='.')
    ax = plt.gca()
    #ax.set_yscale('log')
    #ax.set_xscale('log')
    ax.grid(visible=True, which='major')
    ax.set_xlabel('Change in SLoC [log(lines)]')
    ax.set_ylabel('Change in Area [log(CLBs)]')

    hw_std = np.std(dhw)
    hw_mean = np.mean(dhw)
    hw_median = np.median(dhw)
    print('Mean HW change: '+str(hw_mean))
    print('StD of HW change: '+str(hw_std))
    print('Median HW change: '+str(hw_median))

    sloc_std = np.std(dsloc)
    sloc_mean = np.mean(dsloc)
    sloc_median = np.median(dsloc)
    print('Mean source change: '+str(sloc_mean))
    print('StD of source change: '+str(sloc_std))
    print('Median source change: '+str(sloc_median))

    sloc_hw_cor = np.corrcoef(dsloc, dhw)
    print('Source/HW correlation coefficient: '+str(sloc_hw_cor[0,1]))

    plt.show()

def plot_hw_hist(dhw):
    dhw = np.sort(dhw)
    stop_idx = int(np.floor(dhw.size*0.50))
    print('Total Area measurements: '+str(dhw.size))
    print('Number of Area measurements dropped: '+str(dhw.size - stop_idx))
    ax = plt.gca()
    ax.grid(visible=True, which='major')
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.set_xlabel('Change in Area [CLBs]')
    ax.set_ylabel('Number of Commits')
    #plt.hist(dhw[:stop_idx], [0,1,2,3,4,5,6,7,8,9])
    n, bins, patches = plt.hist(dhw, [0,1,10,100,1000,10000])
    print("Bin values: "+str(n))
    ax.set_xscale('log')
    plt.savefig(os.path.join('util','delta_hw_histogram.png'), bbox_inches='tight')

def main():
    os.chdir('..')

    benchmarks = get_available_benchmarks('benchmarks')
    benchmark_names = benchmarks.keys()

    tool = 'vivado'
    data = {'regex_coprocessor' : None,
            'cva5' : None,
            'zipcpu' : None,
            'jt12' : None,
            'vortex' : None,
           }
    for benchmark_name in benchmark_names:
        char_proj = SetupCharacterizationProjects(benchmarks[benchmark_name], tool)
        projs = char_proj.build_directory_structure()

        tmin_data = collect_tmin_data(projs[1])
        util_data = collect_util_data(projs[1])

        src_stats = get_src_stats(char_proj.cbb)
        data[benchmark_name] = (src_stats, util_data, tmin_data)

    data = repackage_data(data)
    data = reduce_data(data)
    for benchmark in data.keys():
        print(benchmark)
        for idx, item in enumerate(data[benchmark]):
            item = [str(i) for i in item]
            print('\t'+str(idx)+' '+' '.join(item))

    dsloc = []
    dhw = []
    for benchmark_name, deltas in data.items():
        dsloc += [s[0] for s in deltas]
        dhw += [h[1] for h in deltas]
    dsloc = np.array(dsloc)
    dhw = np.array(dhw)

    plot_sloc_vs_hw(dsloc, dhw)
    plot_hw_hist(dhw)
    

if __name__ == '__main__':
    main()
