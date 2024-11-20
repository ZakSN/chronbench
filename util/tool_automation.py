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
    fmax_search_steps = 5
    period_ns = 1

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

    def _result_file_path(self, success, step):
        '''
        Return the path of a result file from the given step
        '''
        if success:
            r = 'PASS'
        else:
            r = 'FAIL'
        return os.path.join(self.proj_dir, self.tool_name+'_'+step+'.'+r)

    def _report_result(self, success, elapsed, step):
        '''
        write a result file to the project directory named
        <tool>_<step>.[PASS|FAIL], that contains the time elapsed to produce
        the result. Also print this information to the terminal.
        '''
        with open(self._result_file_path(success, step), 'w') as f:
            f.write(str(elapsed)+'\n')
        print(self.proj_dir+': '+step+' '+str(success)+', '+str(elapsed))

    def _check_step_complete(self, step):
        '''
        Check to see if a result file for <step> exists.

        Returns true if this step has been run (even if it was unsucessful).

        Prints results to terminal
        '''
        passed_step = os.path.isfile(self._result_file_path(True, step))
        failed_step = os.path.isfile(self._result_file_path(False, step))
        if passed_step:
            print(self.proj_dir+': Nothing to be done -- PASSED '+step)
            return True
        elif failed_step:
            print(self.proj_dir+': Nothing to be done -- FAILED '+step)
            return True
        return False

    def run_synthesis(self):
        '''
        Synthesize the design and report the results (success, and runtime)

        If a synthesis results file all ready exists for this commit skip it
        and print a message.
        '''
        # Check to see if this project has all ready been synthesized
        synth_done = self._check_step_complete('synth')
        if synth_done:
            return

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
        # Check to see if this project has all ready been placed and routed.
        # XXX: Assume this function will only be run after synthesis
        pnr_done = self._check_step_complete('pnr')
        if pnr_done:
            return

        # create the pnr script
        pnr_script = self._build_pnr_script()
        self._write_file(self.proj_dir, self.pnr_script_name, pnr_script)

        start = time.time()
        # run binary search to determine fmax
        last_guess_too_high = None
        coef = 0.5
        guesses = []
        for _ in range(self.fmax_search_steps):

            # guess Tmin == self.period_ns
            inner_start = time.time()
            self._write_sdc(self.period_ns)
            self._run_pnr_tool()
            logfile = os.path.join(self.proj_dir, self.pnr_logfile_name)
            success = self._check_log(logfile, self.pnr_success_msg)
            inner_stop = time.time()
            inner_elapsed = inner_stop - inner_start
            print('\tPNR: '+self.proj_dir+' @ T='+str(self.period_ns)+'ns (RT: '+str(inner_elapsed)+')')

            if success: # self.period_ns too high
                guesses.append(str(self.period_ns)+' too high')
                if last_guess_too_high == False:
                    coef = coef/2
                self.period_ns = self.period_ns*(1-coef)
                last_guess_too_high = True
            else: # self.period_ns too low
                guesses.append(str(self.period_ns)+' too low')
                if last_guess_too_high == True:
                    coef = coef/2
                self.period_ns = self.period_ns*(1+coef)
                last_guess_too_high = False

        stop = time.time()
        elapsed = stop - start

        success = True
        # TODO

        # report the results of the Tmin search
        self._report_result(success, elapsed, 'pnr')
        # record the value of Tmin found
        self._write_file(self.proj_dir, 'tmin.txt', guesses)

    def _build_pnr_script(self):
        pass

    def _write_sdc(self, period):
        '''
        Write and SDC file to constrain the benchmark's clock to <period>
        '''
        clock_name = self.cbb.clock
        sdc = [
            'create_clock -name '+clock_name+' -period '+'{:.2f}'.format(period)+' [get_ports '+clock_name+']',
        ]
        self._write_file(self.proj_dir, self.sdc_name, sdc)

    def _run_pnr_tool(self):
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

    pnr_script_name = 'quartus_pnr_script.tcl'
    pnr_success_msg = 'Quartus Prime Timing Analyzer was successful. 0 errors, 0 warnings'
    pnr_logfile_name = os.path.join('output_files', 'autoqpf.sta.rpt')

    sdc_name = 'quartus_sdc.sdc'
    fmax_search_steps = 10
    period_ns = 6

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
            #'set_global_assignment -name DEVICE 1SG085HN1F43E1VG', # 280k ALM ~ 841k LE
            #'set_global_assignment -name FAMILY "Stratix 10"',
            #'set_global_assignment -name DEVICE 10AX016C3U19E2LG', # 62k ALM ~ 160k LE, 196 user IO
            'set_global_assignment -name DEVICE 10AS016E3F27E1HG', # 62k ALM ~ 240 user IO
            'set_global_assignment -name FAMILY "Arria 10"',
            #'set_global_assignment -name DEVICE 10CX085YF672E5G', # 31k ALM -- No license
            #'set_global_assignment -name FAMILY "Cyclone 10"',
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
        subprocess.run(['quartus_sh', '-t', self.synth_script_name], cwd=self.proj_dir, capture_output=True)
        subprocess.run(['quartus_syn', 'autoqpf'], cwd=self.proj_dir, capture_output=True)

    def _build_pnr_script(self):
        pnr_script = [
            'project_open autoqpf',
            'set_global_assignment -name SDC_FILE '+self.sdc_name,
            'project_close',
        ]
        return pnr_script

    def _run_pnr_tool(self):
        # TODO: optimization -- don't need to add the SDC file everytime
        subprocess.run(['quartus_sh', '-t', self.pnr_script_name], cwd=self.proj_dir, capture_output=True)
        subprocess.run(['quartus_fit', 'autoqpf'], cwd=self.proj_dir, capture_output=True)
        subprocess.run(['quartus_sta', 'autoqpf'], cwd=self.proj_dir, capture_output=True)

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

