import sys
import os
import subprocess

def clone_source_repo(name):
    '''
    git-filter-repo doesn't like submodules, so instead we clone the source repo
    TODO: set base commit
    '''
    source_repos = {'corundum':'https://github.com/corundum/corundum.git'}

    # clone the source repo (git will not overwrite an existing repo)
    subprocess.run(['git', 'clone', source_repos[name]])


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
