import matplotlib.pyplot as plt
import matplotlib
import sys
import os

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
    tmin_data_x = [int(x[0]) for x in tmin_data]
    tmin_data_mid = [(y[1] + y[2])/2 for y in tmin_data]
    tmin_data_unc = [y[1] - y[2] for y in tmin_data]
    return (tmin_data_x, tmin_data_mid, tmin_data_unc)

# TODO: this is Vivado specific
def collect_util_data(proj_list):
    '''
    Read the results of the vivado utilization reports for each project in proj_list

    Returns a sorted 2-tuple formatted as ([commit numbers], [CLB LUT counts])
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
    util_data_x = [int(x[0]) for x in util_data]
    util_data_y = [y[1] for y in util_data]
    return (util_data_x, util_data_y)

def plot_data(to_plot, tool):
    fig = plt.figure()
    gs = plt.GridSpec(5,3, height_ratios=[1,1,0.2,1,1])
    def build_qor_subplot(udim, tdim):
        uax = fig.add_subplot(udim)
        uax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        tax = fig.add_subplot(tdim, sharex=uax)
        uax.tick_params('x', labelbottom=False)
        return (uax, tax)
    axes = dict.fromkeys(to_plot)
    axes['cva5']               = build_qor_subplot(gs[0,0], gs[1,0])
    axes['zipcpu']             = build_qor_subplot(gs[0,1], gs[1,1])
    axes['jt12']               = build_qor_subplot(gs[0,2], gs[1,2])
    fig.add_subplot(gs[2,0]).set_visible(False)
    axes['regex_coprocessor']  = build_qor_subplot(gs[3,0], gs[4,0])
    axes['vortex']             = build_qor_subplot(gs[3,1:], gs[4,1:])

    for bname, subax in axes.items():
        uax = subax[0]
        tax = subax[1]
        uax.grid(visible=True, which='both')
        tax.grid(visible=True, which='both')
        uax.scatter(to_plot[bname][0][0], to_plot[bname][0][1], marker='.')
        tax.errorbar(to_plot[bname][1][0], to_plot[bname][1][1], yerr=to_plot[bname][1][2], fmt='.')
        uax.set_title(bname)

    area_label = 'Area [LUTs]'
    fmax_label = '$f_{max}$ [MHz]'
    commit_label = 'HEAD~<N>'
    axes['cva5'][0].set_ylabel(area_label)
    axes['cva5'][1].set_ylabel(fmax_label)
    axes['regex_coprocessor'][0].set_ylabel(area_label)
    axes['regex_coprocessor'][1].set_ylabel(fmax_label)
    axes['regex_coprocessor'][1].set_xlabel(commit_label)
    axes['vortex'][1].set_xlabel(commit_label)

    plt.gcf().set_size_inches(17, 10)
    plt.savefig(os.path.join('util', tool+'_char_results.png'), bbox_inches='tight')

def main():
    os.chdir('..')

    benchmarks = get_available_benchmarks('benchmarks')
    benchmark_names = benchmarks.keys()

    tool = 'vivado'
    to_plot = {'regex_coprocessor' : None,
               'cva5' : None,
               'zipcpu' : None,
               'jt12' : None,
               'vortex' : None,
              }

    for benchmark_name in to_plot.keys():
        char_proj = SetupCharacterizationProjects(benchmarks[benchmark_name], tool)
        projs = char_proj.build_directory_structure()

        tmin_data = collect_tmin_data(projs[1])
        util_data = collect_util_data(projs[1])

        to_plot[benchmark_name] = (util_data, tmin_data)

    plot_data(to_plot, tool)

if __name__ == '__main__':
    main()
