import matplotlib.pyplot as plt
import sys
import os
import argparse

from characterize_benchmark import SetupCharacterizationProjects
sys.path.insert(1, os.path.join('..'))
from build_benchmark import get_available_benchmarks

def collect_tmin_data(proj_list):
    '''
    Read the results of the F_max binary search (tmin.txt) for each project in
    proj_list.

    Returns a sorted 3-tuple formatted as ([commit numbers], [fmax_mid], [fmax_uncertainty])
    '''
    tmin_data = []
    for path in proj_list:
        commit = str(os.path.split(path)[1]).split('_')[0]
        path = os.path.join(path, 'tmin.txt')
        try:
            with open(path, 'r') as data:
                tmin_list = data.readlines()
                idx = -1
                min_hi = None
                max_lo = None
                while (min_hi is None) or (max_lo is None):
                    if 'too low' in tmin_list[idx]:
                        max_lo = float(tmin_list[idx].split()[0])
                    else:
                        min_hi = float(tmin_list[idx].split()[0])
                    idx = idx - 1
            tmin_data.append((commit, max_lo, min_hi))
        except FileNotFoundError:
            print("WARNING: no T_min data at "+str(path))
    tmin_data = sorted(tmin_data, key=lambda dp: dp[0])
    # convert to fmax:
    # t is in units of ns [1e-9], we want to display MHz (1e6)
    tmin_data = [(x[0], (1/(x[1]*1e-9))/1e6, (1/(x[2]*1e-9))/1e6) for x in tmin_data]
    tmin_data_x = [x[0] for x in tmin_data]
    tmin_data_mid = [(y[1] + y[2])/2 for y in tmin_data]
    tmin_data_unc = [y[1] - y[2] for y in tmin_data]
    return (tmin_data_x, tmin_data_mid, tmin_data_unc)

# TODO: this is Vivado specific
def collect_util_data(proj_list):
    '''
    Read the results of the vivado utilization reports for each project in proj_list

    Returns a sorted 2-tuple formatted as ([commit numbers], [CLB counts])
    '''
    util_data = []
    for path in proj_list:
        commit = str(os.path.split(path)[1]).split('_')[0]
        path = os.path.join(path, 'autoxpr', 'util.log')
        try:
            with open(path, 'r') as data:
                report = data.readlines()
                for line in report:
                    if "CLB LUTs" in line:
                        area = int(line.split('|')[2])
                        break
            util_data.append((commit, area))
        except FileNotFoundError:
            print("WARNING: no utilization log at "+str(path))
    util_data = sorted(util_data, key=lambda dp: dp[0])
    util_data_x = [x[0] for x in util_data]
    util_data_y = [y[1] for y in util_data]
    return (util_data_x, util_data_y)

def plot_data(util_data, tmin_data, tool, benchmark):
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    ax1.grid(visible=True)
    ax2.grid(visible=True)
    ax1.scatter(util_data[0], util_data[1])
    ax2.errorbar(util_data[0], tmin_data[1], yerr=tmin_data[2], fmt='o')
    plt.xticks(rotation=90)
    xlabels = []
    xfirst = 'HEAD'
    xlast = 'HEAD~'+util_data[0][-1]
    for idx in range(len(util_data[0])):
        label = util_data[0][idx]
        if int(label) % 5 == 0:
            xlabels.append(label)
        else:
            xlabels.append('')
    xlabels[0] = xfirst
    xlabels[-1] = xlast
    print(xlabels)
    ax2.set_xticklabels(xlabels)
    ticklabels = ax2.get_xticklabels()
    ticklabels[0].set_rotation(0)
    ticklabels[0].set_ha('left')
    ticklabels[-1].set_rotation(0)
    ticklabels[-1].set_ha('right')
    plt.gca().invert_xaxis()
    ax2.set_xlabel('Commit')
    ax1.set_ylabel('Area [CLBs]')
    ax2.set_ylabel('$F_{max}$ [MHz]')
    fig.suptitle('Area and $F_{max}$ vs. Commit for '+benchmark)
    plt.savefig(os.path.join('util', tool+'_'+benchmark+'_char_results.png'))

def main():
    os.chdir('..')

    parser = argparse.ArgumentParser(
        prog='plot_qor.py',
        description='plot Quality of Results from a timeseries benchmark'
    )

    benchmarks = get_available_benchmarks('benchmarks')
    benchmark_names = benchmarks.keys()

    tools = {
        'vivado' : None,
        #'quartus' : None,
        }

    parser.add_argument('tool', choices=tools.keys(), help='FPGA tool to use')
    parser.add_argument('benchmark_name', choices=benchmark_names, help='benchmark to operate on')

    args = parser.parse_args()

    char_proj = SetupCharacterizationProjects(benchmarks[args.benchmark_name], args.tool)
    projs = char_proj.build_directory_structure()

    tmin_data = collect_tmin_data(projs[1])
    util_data = collect_util_data(projs[1])

    print(tmin_data)
    print(util_data)

    plot_data(util_data, tmin_data, args.tool, args.benchmark_name)

if __name__ == '__main__':
    main()
