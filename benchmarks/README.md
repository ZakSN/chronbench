# Benchmark Description Format
Chronbench benchmarks are specified with benchmark description files. To build
a benchmark `build_benchmark.py` uses the data in a benchmark description file
to do the following major operations:

1. Reduce the upstream repository to its Fileset of Interest
2. Reduce history that modifies the Fileset of Interest to a Window of Interest
3. Squash any unsynthesizable commits left in the Window of Interest.

Additionally, the benchmark description file contains some information about the
design that is to be turned into a benchmark. This information is useful when
an experiment (such as those in `../util`) is carried out on a benchmark
repository.

Benchmark description files are `*.ini` files designed to be parsed by the
Python `configparser` library: https://docs.python.org/3/library/configparser.html.
The format is extremely minimal. For an upstream repository named `benchmark`
the associated description file must be named `benchmark.ini`, and include
exactly one section: `[benchmark]`. The following sections described fields that
may be included in the description file. For `build_benchmark.py` to enumerate
a benchmark description file it must be present in this directory. Thus multiple
benchmark description files for the same upstream repository may be maintained,
as long as only one is kept in this directory.

## Build Fields
The following fields are required by `build_benchmark.py` to build a benchmark
repository.

### `url`
The url to `git clone` the upstream repository from.

### `start`
The full hash of the youngest commit to include in the benchmark repository.
This commit will recieve an internal index of 0 while the benchmark is being
built.

### `depth`
The number of commits to include in the Window of Interest. Note that since
squashing is done after upstream history is reduced to the Window of Interest,
the value of `depth` must account for the number of commits to be squashed.
Further, since the Window of Interest is computed after the Fileset of Interest
simply counting commits from the `start` hash in the upstream repository will
not necessarily yield a correct value for depth, since some of those commits
may exclusively modify uninteresting files.

When developing a benchmark description file it may be helpful to run
`git-filter-repo` with a candidate Fileset of Interest on an upstream repository
to help determine a useful value for `depth`

### `branch`
The name of the branch in the upstream repository to use.

### `fileset`
A list of filepaths in the upstream repository to preserve in the Fileset of
Interest. Note that the `fileset` must be a union of the filepaths required to
synthesize each commit in the benchmark repository.

### `squash-list`
A list of commit indices to squash. Commit must be referenced by index w.r.t.
index 0 (see `start` above). Indices are used instead of hashes since
`git-filter-repo` rewrites history, thereby producing new hashes in the
benchmark repository.

## Experimental Fields
The following fields are included in the benchmark description file to aid in
automating experiments that use a Chronbench benchmark. An example is the
characterization experiments in `../util`.

### `top`
The name of the top module in the design.

### `clock`
The name of the main clock signal in the design.

### `vivado-extra-commands` (optional)
Extra TCL commands to insert in the Vivado build script used by the
characterization experiment in `../util`.

### `vivado-synth-args` (optional)
Extra synthesis arguments for Vivado. Used by the characterization experiment
in `../util`.

### `quartus-extra-commands` (optional)
Extra TCL commands to insert in the Quartus build script used by the
characterization experiment in `../util`.
