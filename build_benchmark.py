import sys
import os
import subprocess
import argparse
import shutil
import configparser

class ChronbenchBenchmark:
    '''
    Manipulate Chronbench Benchmarks.
    '''
    def __init__(self, benchmark_desc_file, relative_gfr_path):
        '''
        Initialize benchmark state
        '''
        self.gfr_path = relative_gfr_path

        benchmark_desc = self._parse_benchmark_desc_file(benchmark_desc_file)
        self.name = benchmark_desc.sections()[0]
        self.benchmark = benchmark_desc[self.name]

        # create variables for all the mandatory benchmark description fields
        self.repo_url = self.benchmark['url']
        self.base_sha = self.benchmark['start']
        self.branch   = self.benchmark['branch']
        self.depth    = self.benchmark['depth']
        self.fileset  = self.benchmark['fileset'].split()
        self.squash_list = self.benchmark['squash-list'].split()

        self.phony_author = 'Chronbench <chronbench@email.com>'

    def build_benchmark(self):
        '''
        Create a fresh benchmark. Result is an incremental benchmark repository.
        '''

        # Step 0 - Get a fresh copy of the upstream repo, and reset it to a
        # known base commit
        self._clone_upstream_repository()
        self._run_cmd('git reset --hard '+self.base_sha)

        # Step 1 - Reduce the upstream repo to the Fileset of Interest
        self._reduce_to_fileset_of_interest()

        # Step 2 - Reduce upstream repo to the Window of Interest
        self._reduce_to_window_of_interest()

        # Step 3 - Squash unsynthesizable commits
        self._squash_unsynthesizable_commits()

    def cleanup_benchmark(self):
        '''
        Delete a benchmark repository so that it can be rebuilt from scratch.
        '''

        isdir = os.path.isdir(self.name)
        if not isdir:
            print("QUITTING: "+self.name+" does not exist!")
            exit()

        shutil.rmtree(self.name)

    def _parse_benchmark_desc_file(self, benchmark_desc_file):
        '''
        Read a benchmark description file. Return a populated config object.
        '''
        config = configparser.ConfigParser()
        config.read(benchmark_desc_file)
        return config

    def _run_cmd(self, cmd):
        '''
        Run a shell command in the benchmark directory. If cmd is a string
        split it on spaces. If it is a list leave it as is. Strings are easier
        to read, but lists allow for some command line fields to include spaces.

        Returns stdout as a list of utf8 strings.
        '''
        if type(cmd) is not list:
            cmd = cmd.split()
        result = subprocess.run(cmd, cwd=self.name, capture_output=True)
        result = result.stdout.decode('utf8').split('\n')
        return result

    def _clone_upstream_repository(self):
        '''
        Clone the upstream repository

        We clone instead of using git submodules, since submodules produce a
        complicated .git/ structure that confuses git-filter-repo.
        '''

        # bailout if the repo all ready exists
        isdir = os.path.isdir(self.name)
        if isdir:
            print("QUITTING: "+self.name+" already exists!")
            print("          perhaps re-run with `--clean`?")
            exit()

        # clone the repo
        subprocess.run(['git', 'clone', self.repo_url])

    def _reduce_to_fileset_of_interest(self):
        '''
        Construct flattening instructions from the fileset and then use the
        fileset and the flattening instructions as input to git-filter-repo to
        rewrite the source repo.

        Result is a hierarchically flat repository (no directories) including
        only commits that modify the Fileset of Interest.
        '''

        # import git-filter-repo
        sys.path.insert(1, self.gfr_path)
        import git_filter_repo as gfr

        # descend into the source repository
        cwd = os.getcwd()
        os.chdir(self.name)

        # blow away everything that is not in the synthesizable fileset and
        # flatten the directory structure
        arg_list = ['--force', '--refs', self.branch]
        for f in self.fileset:
            arg_list.append('--path-match')
            arg_list.append(f)
            arg_list.append('--path-rename')
            arg_list.append(f+':'+os.path.basename(f))

        args = gfr.FilteringOptions.parse_args(arg_list)
        filter = gfr.RepoFilter(args)
        filter.run()

        # return to the original working directory
        os.chdir(cwd)

    def _reduce_to_window_of_interest(self):
        '''
        Create a new root commit equal to HEAD~<depth> and then rebase
        HEAD~<depth>..HEAD onto the new root. We use <depth> rather than a hash
        since gfr produces new commits with unknown hashes.

        Result is a repository with a straightline history including only
        interesting commits.
        '''
        new_branch = self.branch + '_new'

        # HEAD~<depth> is HEAD + depth commits, so correct for ObO
        depth = str(int(self.depth) - 1)

        # get the stop hash
        stop_sha = self._run_cmd('git show -s HEAD~'+depth+' --format=format:%H')[0]

        # create an orphan branch based on the stop commit
        self._run_cmd('git checkout --orphan '+new_branch+' '+stop_sha)
        self._run_cmd(['git', 'commit', '--author', self.phony_author, '-m', 'new root'])

        # rebase the window of interest onto branch using the orphaned new_branch
        # as a base
        self._run_cmd('git rebase --onto '+new_branch+' '+stop_sha+' '+self.branch)

        # get rid of the orphan branch
        self._run_cmd('git branch -D '+new_branch)

    def _squash_unsynthesizable_commits(self):
        '''
        Squash the commits in the squash-list, into their oldest non-squash
        list successor. The squash list is a list of commit indices to squash.
        Must use indices instead of hashes since gfr rewrites hashes. For the
        purposes of the squash-list we assume <branch> is index 0.
        '''
        new_branch = self.branch + '_new'
        squash_shas = []

        # enusre we are starting at index 0
        self._run_cmd('git checkout '+self.branch)

        # get the hash of each commit in the squash list
        for sidx in self.squash_list:
            sha = self._run_cmd('git show -s HEAD~'+sidx+' --format=format:%H')[0]
            squash_shas.append(sha)

        # get hashes for all of the interesting commits
        unsquashed = self._run_cmd('git log --format=format:%H')
        unsquashed.reverse()

        # create a new branch based off the root commit
        self._run_cmd('git checkout '+unsquashed[0])
        self._run_cmd('git checkout -b '+new_branch)

        # cherry-pick each commit from the original branch onto the new branch
        # for commits in the squash list, squash into the subsequent commit
        to_squash = False
        for cidx in range(1, len(unsquashed)):
            self._run_cmd('git cherry-pick '+unsquashed[cidx])

            # Does the last commit need to be squashed into the one just applied
            if to_squash:
                # squash the last two commits, and accept the default message
                self._run_cmd('git reset --hard HEAD~2')
                self._run_cmd('git merge --squash HEAD@{1}')
                self._run_cmd(['git', 'commit', '--no-edit', '--author', self.phony_author])

            # check if the commit we just applied needs to be squashed
            if unsquashed[cidx] in squash_shas:
                to_squash = True
            else:
                to_squash = False

        # delete the unsquashed branch and rename the squashed branch
        self._run_cmd('git branch -D '+self.branch)
        self._run_cmd('git branch -m '+new_branch+' '+self.branch)


def get_available_benchmarks(benchmark_dir):
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

    benchmarks = get_available_benchmarks('benchmarks')
    benchmark_names = benchmarks.keys()

    parser.add_argument('benchmark_name', choices=benchmark_names, help='build the named benchmark')
    parser.add_argument('-c', '--clean', action='store_true', help='cleanup the named benchmark')

    args = parser.parse_args()

    cbb = ChronbenchBenchmark(benchmarks[args.benchmark_name], 'git-filter-repo')
    if args.clean:
        cbb.cleanup_benchmark()
    else:
        cbb.build_benchmark()

if __name__ == '__main__':
    main()
