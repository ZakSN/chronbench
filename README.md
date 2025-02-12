# Chronbench: An Incremental HDL Benchmark Suite
FPGA CAD tools are often intended to compile an entire design from scratch to maximize the quality of results.
Even with modern CAD algorithms this is a slow process.
This paradigm limits designer productivity during incremental development, since every development iteration must endure the entire compilation process.
Many vendor tools therefore offer `incremental modes' that partially reuse compilation results to accelerate development at the HDL level of abstraction.
Unfortunately, there is limited academic research into more sophisticated incremental HDL flows.
We believe a key obstacle to research in this area is the lack of benchmarks which encapsulate realistic HDL development histories.
As such we introduce Chronbench, a suite of HDL benchmarks which encapsulate development history as a chronological series of synthesizable commits in a git repository.
In addition to five such benchmarks we present a tool for converting a public repository into a into a Chronbench benchmark.
Further, we synthesize, place, and route 170  commits in order to fully characterize the suite.
Finally, we analyze the characterization data to produce some key insights about the relative magnitude of HDL development changes and observe that approximately half of real development commits do not significantly impact device utilization, indicating significant potential for reuse during HDL development.

# Anonymous Benchmark Downloads
1. regex_coprocessor (Unavailable to ensure license compatibility)
2. [cva5](https://osf.io/download/pj6nu/?view_only=eea52a99d44c426fb1c3a5eab9d15a3f)
3. [zipcpu](https://osf.io/download/u3xe7/?view_only=eea52a99d44c426fb1c3a5eab9d15a3f)
4. [jt12](https://osf.io/download/gudyt/?view_only=eea52a99d44c426fb1c3a5eab9d15a3f)
5. [vortex](https://osf.io/download/3dfkb/?view_only=eea52a99d44c426fb1c3a5eab9d15a3f)

# Usage
The following sections discuss how to use Chronbench.

## Building Benchmarks Locally
Note: when cloning Chronbench remember to also clone submodules in order to bring in the `git-filter-repo` dependency

To create a Chronbench development history benchmark run:

```
python build_benchmark.py ${BENCHMARK_NAME}
```

Benchmarks are specified with a benchmark description file in the `benchmarks/` directory.
`build_benchmark.py` automatically enumerates this directory, thus to see a list of available benchmarks simply run:

```
python build_benchmark.py -h
```

After running `build_benchmark.py` a directory called `BENCHMARK_NAME` will be created along side the script.
This directory is a development history benchmark, packaged as a git repository.
To rebuild a benchmark the corresponding directory must be removed. This can be done by running:

```
python build_benchmark.py -c
```

To produce some of the graphics in the Chronbench paper it is necessary to collect benchmark statistics.
This can be done by building a benchmark as:

```
python build_benchmark.py ${BENCHMARK_NAME} -s
```

Which clean builds the benchmark and writes a file called `${BENCHMARK_NAME}_statistics.txt` alongside the benchmark directory.

## Building Benchmarks With Github Actions
The `.github/workflows` directory includes a github actions workflow to build all available benchmarks.
To run this workflow:
1. fork the repository
2. select the 'Actions' tab in the fork
3. select the 'Build Suite' Action
4. Click the 'Run workflow' dropdown and select the 'main' branch

Note: The 'Build Suite' action is also automatically run everytime a commit is pushed to the 'main' branch.

To view the outputs of the 'Build Suite' action select a run, and scroll to the artifacts section.
The artifacts available to download are the development history benchmarks.
Alternatively, the links above can be used to download a copy of these artifacts.

## Running the Characterization Experiments

Once a benchmark has been built in the repo's root directory a characterization experiment can be run with the `util/characterize_benchmark.py` script.
To run a characterization experiment:

```
python characterize_benchmark.py ${TOOL} ${STEP} ${BENCHMARK_NAME} -j${N}
```

This script runs the experiment described in Section 6.2 of the Chronbench paper.
effectively `${TOOL}` is run on each commit in `${BENCHMARK_NAME}` up to `${STEP}` with as many as `${N}` commits being processed in parallel.
For example to generate the data plotted in Figure 8, subfigure cva5 the following command would be run:

```
python characterize_benchmark.py vivado pnr cva5 -j8
```

Which places and routes each commit in cva5 with vivado, running upto 8 instances of vivado at the same time.
See the `-h` option for other configurations.

Note: Running a full characterization sweep is slow and resources intensive, since each commit must be fully compiled many times to search for Fmax.

Note: The script assumes that the `vivado` command is on the ${PATH}

Once complete a directory called `${BENCHMARK_NAME}_${TOOL}_char_projects` will be created.
Within this directory should be a subdirectory for each commit in the benchmark.

## Building Graphics:
Upon completion of all five characterization sweep the plots from Figures 6, 8, and 9 can be built by running the `plot_*.py` scripts in the `util/` directory.

Note these scripts depend on matplotlib, and may require some fiddling with the local python environment to run properly.
