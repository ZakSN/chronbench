# Chronbench: An Incremental HDL Benchmark Suite
FPGA CAD tools are often intended to map an entire design to a device from scratch to maximize the quality of results.
Even with modern CAD algorithms this is a slow process.
This paradigm limits designer productivity during incremental development, since every development iteration must endure the entire mapping process.
Many vendor tools therefore offer `incremental modes' that partially reuse mapping results to accelerate development at the HDL level of abstraction.
Unfortunately, there is limited academic research into more sophisticated incremental HDL flows.
We believe a key obstacle to research in this area is the lack of benchmarks which encapsulate realistic HDL development histories.
As such we introduce Chronbench, a suite of HDL benchmarks which encapsulate development history as a chronological series of synthesizable commits in a \texttt{git} repository.
In addition to five such benchmarks we present a tool for converting a public repository into a into a Chronbench benchmark.
Further, we synthesize, place, and route 170  commits in order to fully characterize the suite.
Finally, we analyze the characterization data to produce some key insights about the relative magnitude of HDL development changes and observe that approximately half of real development commits do not significantly impact device utilization, indicating significant potential for reuse during HDL development.
