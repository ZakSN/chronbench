import matplotlib.pyplot as plt
import os
import numpy as np

def read_stats_files(to_plot):
    commit_data = []
    bulk_data = {}
    for bmark in to_plot:
        data = []
        in_cb = 0
        with open(os.path.join('..', bmark + '_statistics.txt'), 'r') as df:
            lines = df.readlines()
            for line in lines:
                line = line.split()
                ctype = 0
                for switch in line[2:]:
                    if switch == 'True':
                        ctype = ctype + 1
                if ctype == 2:
                    in_cb = in_cb + 1
                if line[1] != 'None':
                    data.append((int(line[0]), int(line[1]), ctype))
                else:
                    data.append((int(line[0]), 0, ctype))
        data = sorted(data, key=lambda commit: commit[0])
        print(bmark+' total: '+str(len(data))+', chronbench: '+str(in_cb))
        bulk_data[bmark] = (len(data), in_cb)
        commit_data.append(data)
    return commit_data, bulk_data

def draw_stripchart(to_plot, commit_data):
    fig, ax = plt.subplots(len(to_plot), 1, sharex=False)

    for idx in range(len(to_plot)):
        z_data = np.array([x[2] for x in commit_data[idx]])
        z_data = np.vstack((z_data,z_data))
        y_data = np.arange(0,3)
        x_data = np.arange(0, len(commit_data[idx])+1)

        ax[idx].pcolormesh(x_data, y_data, z_data)
        ax[idx].get_yaxis().set_ticklabels([])
    return fig, ax

def draw_barchart(to_plot, commit_data):
    fig, ax = plt.subplots(len(to_plot), 1, sharex=False)
    for idx in range(len(to_plot)):
        c_data = np.array([x[2] for x in commit_data[idx]])
        #y_data = np.random.random(len(commit_data[idx]))
        y_data = np.array([x[1] for x in commit_data[idx]])
        x_data = np.arange(0, len(commit_data[idx]))

        barlist = ax[idx].bar(x_data, y_data, width=1)
        for bidx in range(len(barlist)):
            barlist[bidx].set_color(plt.colormaps['viridis'](c_data[bidx]/2))
        ax[idx].set_yscale('symlog')
        ax[idx].margins(0.0)
    return fig, ax

def label_chart(to_plot, fig, ax, name, bulk_data):
    for idx in range(len(to_plot)):
        ax[idx].set_title(to_plot[idx])
        ax[idx].set_ylabel(bulk_data[to_plot[idx]][1],
                           rotation=0,
                           horizontalalignment='right',
                           verticalalignment='center',
                           backgroundcolor=plt.colormaps['viridis'](1.0))
        ticklabels = ax[idx].get_yticklabels()
        top = ticklabels[0]
        bottom = ticklabels[-1]
        for yidx in range(len(ticklabels)):
            if ticklabels[yidx].get_text() != '$\\mathdefault{0}$':
                ticklabels[yidx] = ''
        ticklabels[0] = top
        ticklabels[-1] = bottom
        ax[idx].set_yticklabels(ticklabels)
        ax[idx].yaxis.tick_right()
        ax[idx].set_xticks(list(ax[idx].get_xticks()) + [bulk_data[to_plot[idx]][0]])
        xticklabels = ax[idx].get_xticklabels()
        for xtick in range(len(xticklabels)):
            xticklabels[xtick].set_ha('right')
        xticklabels[-1].set_ha('left')
        ax[idx].set_xticklabels(xticklabels)
        ax[idx].set_xlim(0, bulk_data[to_plot[idx]][0])
    ax[-1].set_xlabel('Commit Number')
    nhw = plt.Line2D([],[], color=plt.colormaps['viridis'](0.0), label='Non-HDL')
    uhw = plt.Line2D([],[], color=plt.colormaps['viridis'](0.5), label='HDL')
    hw = plt.Line2D([],[], color=plt.colormaps['viridis'](1.0), label='Chronbench')
    fig.legend(handles=[nhw, uhw, hw], loc = 'lower center', ncols=3, bbox_to_anchor=(0.5, -0.05))
    fig.subplots_adjust(hspace=1.3)
    plt.savefig(name, bbox_inches='tight')
    #plt.show()

def main():
    to_plot = ['regex_coprocessor', 'cva5', 'zipcpu', 'jt12', 'vortex']
    commit_data, bulk_data = read_stats_files(to_plot)

    fig, ax = draw_stripchart(to_plot, commit_data)
    label_chart(to_plot, fig, ax, 'chronbench_stripchart.png', bulk_data)
    fig, ax = draw_barchart(to_plot, commit_data)
    label_chart(to_plot, fig, ax, 'chronbench_barchart.png', bulk_data)

if __name__ == '__main__':
    main()
