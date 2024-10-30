import sys
import os
import subprocess
import argparse
import shutil
import configparser

def clone_source_repo(benchmark):
    '''
    Clone the source repo, and reset it to the base commit. The `benchmark`
    object includes the url and base commit.

    We clone instead of using git submodules, since submodules produce a
    complicated .git/ structure that confuses git-filter-repo.
    '''

    name = benchmark.sections()[0]
    repo_url = benchmark[name]['url']

    # bailout if the repo all ready exists
    isdir = os.path.isdir(name)
    if isdir:
        print("QUITTING: "+name+" already exists!")
        print("          perhaps re-run with `--clean`?")
        exit()

    # clone the source repo
    subprocess.run(['git', 'clone', repo_url])

def reset_source_repo_head(benchmark):
    '''
    Set the HEAD of the source repo to the start commit
    '''
    name = benchmark.sections()[0]
    base_sha = benchmark[name]['start']

    # reset the source repo to the base commit
    subprocess.run(['git', 'reset', '--hard', base_sha], cwd=name)

def domesticate_source_repo(benchmark, relative_gfr_path):
    '''
    Construct flattening instructions from the fileset and then use the fileset
    and the flattening instructions to rewrite the source repo.

    result is a "domesticated" (i.e. suitable as a benchmark) repository
    '''

    sys.path.insert(1, relative_gfr_path)
    import git_filter_repo as gfr

    name = benchmark.sections()[0]
    fileset = benchmark[name]['fileset'].split()
    branch = benchmark[name]['branch']

    # descend into the source repository
    cwd = os.getcwd()
    os.chdir(name)

    # blow away everything that is not in the synthesizable fileset and flatten
    # the directory structure
    arg_list = ['--force', '--refs', branch]
    for f in fileset:
        arg_list.append('--path-match')
        arg_list.append(f)
        arg_list.append('--path-rename')
        arg_list.append(f+':'+os.path.basename(f))

    args = gfr.FilteringOptions.parse_args(arg_list)
    filter = gfr.RepoFilter(args)
    filter.run()

    # return to the original working directory
    os.chdir(cwd)

def truncate_filtered_repo(benchmark):
    '''
    Create a new root commit equal to HEAD~<depth> and then rebase
    HEAD~<depth>..HEAD onto the new root. We use <depth> rather than a SHA since
    gfr produces new commits with unknown hashes.
    '''
    name = benchmark.sections()[0]
    branch = benchmark[name]['branch']
    new_branch = branch + "_new"
    start_sha = benchmark[name]['start']
    depth = benchmark[name]['depth']

    # HEAD~<depth> is HEAD + depth commits, so correct for ObO
    depth = str(int(depth) - 1)

    # get the stop SHA
    stop_sha = subprocess.run(['git', 'show', '-s', 'HEAD~' + depth, '--format=format:%H'], cwd=name, capture_output=True)
    stop_sha = stop_sha.stdout.decode('utf8')

    # create an orphan branch based on the stop commit
    subprocess.run(['git', 'checkout', '--orphan', new_branch, stop_sha], cwd=name)
    subprocess.run(['git', 'commit', '--author', 'Chronbench <chronbench@email.com>', '-m', 'new root'], cwd=name)

    # rebase the window of interest onto branch using the orphaned new_branch
    # as a base
    subprocess.run(['git', 'rebase', '--onto', new_branch, stop_sha, branch], cwd=name)

    # get rid of the orphan branch
    subprocess.run(['git', 'branch', '-D', new_branch], cwd=name)


def cleanup_benchmark(benchmark):
    '''
    delete a benchmark repository, so that it can be rebuilt from scratch.
    '''

    name = benchmark.sections()[0]
    isdir = os.path.isdir(name)
    if not isdir:
        print("QUITTING: "+name+" does not exist!")
        exit()

    shutil.rmtree(name)

def read_benchmark_config(benchmark):
    '''
    Read a benchmark initialization file, and return the populated config object.
    '''
    config = configparser.ConfigParser()
    config.read(benchmark)
    return config

def get_benchmarks(benchmark_dir):
    '''
    Check the `benchmark_dir` for .ini config files. Config files are assumed
    to be named the same as the source repo.

    Return a dictionary of the form:
        benchmark_name : path/to/config_file
    '''
    benchmarks = {}
    for b in os.listdir(benchmark_dir):
        bpath = os.path.join(benchmark_dir, b)
        if os.path.isfile(bpath) and b.endswith('.ini'):
            benchmarks[os.path.splitext(b)[0]] = bpath
    return benchmarks

def main():
    parser = argparse.ArgumentParser(
        prog='build_benchmark.py',
        description='build a timeseries HDL benchmark'
    )

    benchmarks = get_benchmarks('benchmarks')
    benchmark_names = benchmarks.keys()

    parser.add_argument('benchmark_name', choices=benchmark_names, help='build the named benchmark')
    parser.add_argument('-c', '--clean', action='store_true', help='cleanup the named benchmark')

    args = parser.parse_args()

    benchmark = read_benchmark_config(benchmarks[args.benchmark_name])

    if args.clean:
        cleanup_benchmark(benchmark)
    else:
        clone_source_repo(benchmark)
        reset_source_repo_head(benchmark)
        domesticate_source_repo(benchmark, 'git-filter-repo')
        truncate_filtered_repo(benchmark)

if __name__ == '__main__':
    main()
