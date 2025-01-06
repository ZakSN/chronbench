import matplotlib.pyplot as plt
import matplotlib
import sys
import os
import numpy as np

from plot_qor import collect_tmin_data
from plot_qor import collect_util_data
from plot_stats import read_stats_files
from characterize_benchmark import SetupCharacterizationProjects
sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks

def reduce_data(data):
    for benchmark_name, benchmark_data in data.items():
        # reduce to interesting commits
        commit_data = benchmark_data[0]
        interesting_commit_data = []
        for commit in commit_data:
            if commit[2] == 2:
                interesting_commit_data.append(commit)
        data[benchmark_name][0] = list(reversed(interesting_commit_data))

        # repackage everything into a more useful format
        # TODO: this is pretty ugly, but basically we have to read the squash
        # to squash stats from interesting commits to align them with QoR data
        # better way to do this may be to read directly from a benchmark repo
        reduced = []
        squash_list = data[benchmark_name][1]
        synth_idx = 0
        for real_idx in range(len(data[benchmark_name][0])+1):
            try:
                ts = data[benchmark_name][0][real_idx][0]
                deltasloc = data[benchmark_name][0][real_idx][1]
            except IndexError:
                ts = None
                deltasloc = None
            if real_idx not in squash_list:
                print('adding '+str(real_idx)+' as '+str(synth_idx))
                util = data[benchmark_name][2][1][synth_idx]
                fmid = data[benchmark_name][3][1][synth_idx]
                frange = data[benchmark_name][3][2][synth_idx]
                reduced.append((ts, deltasloc, util, fmid, frange, False))
                synth_idx += 1
            else:
                print('squashing '+str(real_idx)+' into '+str(len(reduced)-1)+' ('+str(synth_idx)+')')
                squash = reduced[-1]
                squash = (squash[0], squash[1] + deltasloc, squash[2], squash[3], squash[4], True)
                reduced[-1] = squash
        data[benchmark_name] = reduced
    return data

def compute_qor_deltas(data):
    deltas = dict.fromkeys(data)
    for benchmark_name, benchmark_data in data.items():
        qor_delta = []
        for idx in range(len(benchmark_data) - 1):
            N  = benchmark_data[idx]
            dN = benchmark_data[idx+1]
            qor_delta.append((
                N[0],
                N[1],
                abs(N[2] - dN[2]),
                abs(N[3] - dN[3]),
                abs(N[4] - dN[4])
            ))
        deltas[benchmark_name] = qor_delta
    return deltas

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

    benchmark_names = data.keys()

    for benchmark_name in benchmark_names:
        char_proj = SetupCharacterizationProjects(benchmarks[benchmark_name], tool)
        projs = char_proj.build_directory_structure()

        tmin_data = collect_tmin_data(projs[1])
        util_data = collect_util_data(projs[1])

        squash_list = char_proj.cbb.squash_list
        squash_list = [int(s) for s in squash_list]

        data[benchmark_name] = (squash_list, util_data, tmin_data)

    os.chdir('util')
    commit_data, _ = read_stats_files(benchmark_names)
    os.chdir('..')

    for idx, benchmark_name in enumerate(benchmark_names):
        data[benchmark_name] = [commit_data[idx], *data[benchmark_name]]

    data = reduce_data(data)
    deltas = compute_qor_deltas(data)

    def print_data_dict(data):
        for benchmark in data.keys():
            print(benchmark)
            for idx, item in enumerate(data[benchmark]):
                item = [str(i) for i in item]
                print('\t'+str(idx)+' '+' '.join(item))
    print_data_dict(data)
    print_data_dict(deltas)

    dsloc = []
    dhw = []
    for benchmark_name, data in deltas.items():
        dsloc += [s[1] for s in data]
        dhw += [h[2] for h in data]
    dsloc = np.array(dsloc)
    dhw = np.array(dhw)

    plot_sloc_vs_hw(dsloc, dhw)
    plot_hw_hist(dhw)

if __name__ == '__main__':
    main()
