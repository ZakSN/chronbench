import os
import subprocess
import time

class AbstractFPGATool:
    '''
    Abstract class for automating FPGA flows over a Chronbench Benchmark
    '''
    tool_name = 'ABSTRACT'
    synth_script_name  = 'ABSTRACT_synth_script.tcl'
    synth_success_msg  = 'ABSTRACT SYNTH SUCCESS'
    synth_logfile_name = 'synth_log'
    pnr_script_name = 'ABSTRACT_pnr_script.tcl'
    pnr_success_msg = 'ABSTRACT PNR SUCCESS'
    pnr_logfile_name = 'pnr_log'
    sdc_name = 'ABSTRACT.sdc'

    def __init__(self, proj_dir, chronbench_benchmark):
        self.proj_dir = proj_dir
        self.cbb = chronbench_benchmark

    def _write_file(self, path, name, contents):
        '''
        Write a file to /path/name, containing contents.
        '''
        f = os.path.join(path, name)
        with open(f, 'w') as to_write:
            for line in contents:
                to_write.write(line+'\n')

    def _check_log(self, logfile, success_msg):
        '''
        Check each line of logfile to see if it contains success_msg.
        '''
        with open(logfile, 'r') as log:
            loglines = log.readlines()
        for line in loglines:
            if success_msg in line:
                return True
        return False

    def _report_result(self, success, elapsed, step):
        '''
        write a result file to the project directory named
        <tool>_<step>.[PASS|FAIL], that contains the time elapsed to produce
        the result. Also print this information to the terminal.
        '''
        if success:
            r = 'PASS'
        else:
            r = 'FAIL'
        with open(os.path.join(self.proj_dir, self.tool_name+'_'+step+r), 'w') as f:
            f.write(r+'\n')
            f.write(str(elapsed)+'\n')
        print(self.proj_dir+': '+r+", "+str(elapsed))

    def run_synthesis(self):
        '''
        Synthesize the design and report the results (success, and runtime)
        '''
        # create the synthesis script
        synth_script = self._build_synth_script()
        self._write_file(self.proj_dir, self.synth_script_name, synth_script)
        
        # run the synthesis tool
        start = time.time()
        self._run_synthesis_tool()
        stop = time.time()
        elapsed = stop - start

        # report the results of synthesis
        logfile = os.path.join(self.proj_dir, self.synth_logfile_name)
        success = self._check_log(logfile, self.synth_success_msg)
        self._report_result(success, elapsed, 'synth')

    def _build_synth_script(self):
        pass

    def _run_synthesis_tool(self):
        pass

    def run_pnr(self):
        '''
        Iteratively Place and Route the design to search for Fmax and report
        the results (Fmax, Area, runtime)
        '''
        #TODO
        pass

class Quartus(AbstractFPGATool):
    '''
    Use Quartus to synthesize, place, and route a commit level synthesis
    project.

    Assumes Quartus executables are on the system path
    '''
    tool_name = 'quartus'
    synth_script_name = 'quartus_synth_script.tcl'
    synth_success_msg  = 'Info: Successfully synthesized'
    synth_logfile_name = os.path.join('output_files', 'autoqpf.syn.rpt')
    pnr_script_name = None
    pnr_success_msg = None
    pnr_logfile_name = None
    sdc_name = None

    def _build_synth_script(self):
        '''
        Create a tcl script to run Quartus Synthesis
        '''
        # check for Quartus specific hacks
        try:
            quartus_extra_commands = self.cbb.benchmark['quartus-extra-commands'].split('\n')
        except:
            quartus_extra_commands = ''

        # get the benchmark top module
        top = self.cbb.benchmark['top']

        # create the synth script
        synth_script = [
            'project_new autoqpf -overwrite',
            'set_global_assignment -name TOP_LEVEL_ENTITY '+top,
            'set_global_assignment -name DEVICE 1SG085HN1F43E1VG',
            'set_global_assignment -name FAMILY "Stratix 10"',
            'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
            *quartus_extra_commands,
            'set sources [glob src/*]',
            'foreach src $sources {',
            '    set ext [file extension $src]',
            '    switch $ext {',
            '        .v -',
            '        .vh {set filetype VERILOG_FILE}',
            '        .sv -',
            '        .svh {set filetype SYSTEMVERILOG_FILE}',
            '        .vdh {set filetype VHDL_FILE}',
            '    }',
            '    set_global_assignment -name $filetype $src',
            '}',
            'project_close',
        ]
        return synth_script

    def _run_synthesis_tool(self):
        '''
        Use quaruts to build a project from the source files and then
        synthesize that project. Assumes Quartus executables are on the path
        '''
        subprocess.run(['quartus_sh', '-t', 'quartus_synth_script.tcl'], cwd=self.proj_dir, capture_output=True)
        subprocess.run(['quartus_syn', 'autoqpf'], cwd=self.proj_dir, capture_output=True)

class Vivado(AbstractFPGATool):
    '''
    Use Vivado to synthesize, place and route a commit level synthesis project.

    Assumes Vivado executables are on the system path
    '''
    tool_name = 'vivado'
    synth_script_name = 'vivado_synth_script.tcl'
    synth_success_msg  = 'synth_design completed successfully'
    synth_logfile_name = 'vivado.log'
    pnr_script_name = None
    pnr_success_msg = None
    pnr_logfile_name = None
    sdc_name = None


    def _build_synth_script(self):
        '''
        Create a tcl script to run Vivado synthesis
        '''
        # Check for any Vivado specific hacks
        try:
            vivado_extra_commands = self.cbb.benchmark['vivado-extra-commands'].split('\n')
        except:
            vivado_extra_commands = ''
        try:
            vivado_synth_args = self.cbb.benchmark['vivado-synth-args']
        except:
            vivado_synth_args = ''

        # get the benchmark top module
        top = self.cbb.benchmark['top']

        # create the synth script
        synth_script = [
            'set outputdir autosynthxpr',
            'set project autosynth',
            'set partnumber xcvu3p-ffvc1517-3-e',
            'file mkdir $outputdir',
            'create_project -part $partnumber $project $outputdir',
            *vivado_extra_commands,
            'add_files src',
            'set synth_args {'+vivado_synth_args+'}',
            'catch {synth_design -top '+top+' {*}$synth_args}',
            'exit',
        ]
        return synth_script

    def _run_synthesis_tool(self):
        '''
        Run Vivado in headless mode to execute the synthscript in the commit
        level project directory. Assume Vivado is on the path.
        '''
        subprocess.run(['vivado', '-mode', 'tcl', '-source', self.synth_script_name], cwd=self.proj_dir, capture_output=True)

