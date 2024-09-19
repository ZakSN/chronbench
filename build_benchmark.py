import sys
import os
import subprocess

'''
dictionary containing all of the repos which we can turn into benchmarks
key: name of directory produced by git cloning
value: (url to clone, base hash to build benchmark from)
'''
source_repos = {
    'corundum':('https://github.com/corundum/corundum.git','1ca0151b97af85aa5dd306d74b6bcec65904d2ce')
}

def clone_source_repo(name):
    '''
    Clone the repo called `name` (which must also be a key in source_repos), and
    reset it to the base commit.

    We clone instead of using git submodules, since submodules produce a
    complicated .git/ structure that confuses git-filter-repo.
    '''

    repo_url = source_repos[name][0]
    base_sha = source_repos[name][1]

    # bailout if the repo all ready exists
    isdir = os.path.isdir(name)
    if isdir:
        print("QUITTING: "+name+" already exists!")
        exit()

    # clone the source repo
    subprocess.run(['git', 'clone', repo_url])

    # reset the source repo to the base commit
    subprocess.run(['git', 'reset', '--hard', base_sha], cwd=name)

    # purge the reflog so that we don't trigger safety checks in git-filter-repo
    subprocess.run(['git', 'reflog', 'delete', 'HEAD@{1}'], cwd=name)


def main():
    benchmark_name = sys.argv[1]
    data_dir = 'filesets'
    gfr = os.path.join('git-filter-repo','git-filter-repo')

    clone_source_repo(benchmark_name)

    # read the file set
    fileset_file = benchmark_name + '_fileset.txt'
    with open(os.path.join(data_dir, fileset_file), 'r') as f:
        fileset = f.readlines()

    # write out a rename set
    filter_file = benchmark_name + '_filter.txt'
    with open(os.path.join(data_dir, filter_file), 'w') as f:
        for file in fileset:
            file = file[:-1] # strip newline
            f.write(file+'==>'+os.path.basename(file)+'\n') # flattening rename

    # run the filter command to flatten the repo
    cwd = os.getcwd()
    os.chdir(benchmark_name)
    fileset_path = os.path.join('..',data_dir,fileset_file)
    filter_path = os.path.join('..',data_dir,filter_file)
    gfr_path = os.path.join('..',gfr)
    # blow away everything that is not in the synthesizable fileset
    subprocess.run([gfr_path, '--paths-from-file', fileset_path])
    # flatten remaining directory structure
    subprocess.run([gfr_path, '--paths-from-file', filter_path])

if __name__ == '__main__':
    main()
