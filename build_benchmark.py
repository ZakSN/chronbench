import sys
import os
import subprocess
import argparse
import shutil

'''
dictionary containing all of the repos which we can turn into benchmarks
key: name of directory produced by git cloning
value: (url to clone, base hash to build benchmark from)
'''
SOURCE_REPOS = {
    'corundum':('https://github.com/corundum/corundum.git','1ca0151b97af85aa5dd306d74b6bcec65904d2ce')
}

'''
locations of the:
    - (manually constructed) synthesis filesets
    - git-filter-repo executable
relative to this file
'''
FILESET_DIR = 'filesets'
GFR_EXE = os.path.join('git-filter-repo','git-filter-repo')

def clone_source_repo(name):
    '''
    Clone the repo called `name` (which must also be a key in source_repos), and
    reset it to the base commit.

    We clone instead of using git submodules, since submodules produce a
    complicated .git/ structure that confuses git-filter-repo.
    '''

    repo_url = SOURCE_REPOS[name][0]
    base_sha = SOURCE_REPOS[name][1]

    # bailout if the repo all ready exists
    isdir = os.path.isdir(name)
    if isdir:
        print("QUITTING: "+name+" already exists!")
        print("          perhaps re-run with `--clean`?")
        exit()

    # clone the source repo
    subprocess.run(['git', 'clone', repo_url])

    # reset the source repo to the base commit
    subprocess.run(['git', 'reset', '--hard', base_sha], cwd=name)

    # purge the reflog so that we don't trigger safety checks in git-filter-repo
    subprocess.run(['git', 'reflog', 'delete', 'HEAD@{1}'], cwd=name)

def domesticate_source_repo(name):
    '''
    Construct flattening instructions from the fileset and then use the fileset
    and the flattening instructions to rewrite the source repo.

    result is a "domesticated" (i.e. suitable as a benchmark) repository in
    `name`
    '''

    # read the fileset file
    fileset_file = name + '_fileset.txt'
    with open(os.path.join(FILESET_DIR, fileset_file), 'r') as f:
        fileset = f.readlines()

    # build flattening instructions from the fileset
    filter_file = name + '_filter.txt'
    with open(os.path.join(FILESET_DIR, filter_file), 'w') as f:
        for file in fileset:
            file = file[:-1] # strip newline
            f.write(file+'==>'+os.path.basename(file)+'\n') # flattening rename

    # run the filter command to flatten the repo
    fileset_path = os.path.join('..',FILESET_DIR,fileset_file)
    filter_path = os.path.join('..',FILESET_DIR,filter_file)
    gfr_path = os.path.join('..',GFR_EXE)

    # blow away everything that is not in the synthesizable fileset
    subprocess.run([gfr_path, '--paths-from-file', fileset_path], cwd=name)
    # flatten remaining directory structure
    subprocess.run([gfr_path, '--paths-from-file', filter_path], cwd=name)

def cleanup_benchmark(name):
    '''
    delete a benchmark repository, so that it can be rebuilt from scratch.
    '''

    isdir = os.path.isdir(name)
    if not isdir:
        print("QUITTING: "+name+" does not exist!")
        exit()

    shutil.rmtree(name)

def main():
    parser = argparse.ArgumentParser(
        prog='build_benchmark.py',
        description='build a timeseries HDL benchmark'
    )

    benchmark_names = (SOURCE_REPOS.keys())

    parser.add_argument('benchmark_name', choices=benchmark_names, help='build the named benchmark')
    parser.add_argument('-c', '--clean', action='store_true', help='cleanup the named benchmark')

    args = parser.parse_args()

    if args.clean:
        cleanup_benchmark(args.benchmark_name)
    else:
        clone_source_repo(args.benchmark_name)
        domesticate_source_repo(args.benchmark_name)


if __name__ == '__main__':
    main()
