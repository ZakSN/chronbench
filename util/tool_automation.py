import os
import subprocess
import time

class SynthesisTool:
    '''
    A generic synthesis tool class
    '''
    tool_name = 'GENERIC'
    synth_script_name = 'GENERIC_synth_script.tcl'
    success_msg = 'GENERIC SUCCESS'
    logfile_name = 'path_to_synth_log'

    def __init__(self, proj_dir, cbb):
        self.proj_dir = proj_dir
        self.cbb = cbb

    def run_synthesis(self):
        self._build_synth_script()
        self._write_synth_script()
        self._run_tool()
        self._report_result()

    def _build_synth_script(self):
        pass

    def _write_synth_script(self):
        self.synth_script_path = os.path.join(self.proj_dir, self.synth_script_name)
        with open(self.synth_script_path, 'w') as script:
            for line in self.synth_script:
                script.write(line+'\n')

    def _run_tool(self):
        start = time.time()
        self._run_tool_wrapped()
        stop = time.time()
        self.elapsed = stop - start

    def _report_result(self):
        '''
        Check to see if synthesis was successful.
        '''
        # read the log to see if synthesis was successful
        logfile = os.path.join(self.proj_dir, self.logfile_name)
        with open(logfile, 'r') as log:
            synth_result = log.readlines()

        success = False
        for line in synth_result:
            if self.success_msg in line:
                success = True

        # print a message to the terminal and write a PASS/FAIL file
        if success:
            r = 'PASS'
        else:
            r = 'FAIL'
        with open(os.path.join(self.proj_dir, self.tool_name + '_synth.'+r), 'w') as f:
            f.write(r+'\n')
            f.write(str(self.elapsed)+'\n')
        print(self.proj_dir+': '+r+", "+str(self.elapsed))

class QuartusSynthesis(SynthesisTool):
    '''
    Use Quartus to synthesize a commit level synthesis project.

    Assumes Quartus executables are on the system path
    '''
    tool_name = 'quartus'
    synth_script_name = 'quartus_synth_script.tcl'
    success_msg = 'Info: Successfully synthesized'
    logfile_name = os.path.join('output_files', 'autoqpf.syn.rpt')

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
        self.synth_script = [
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

    def _run_tool_wrapped(self):
        '''
        Use quaruts to build a project from the source files and then
        synthesize that project. Assumes Quartus executables are on the path
        '''
        subprocess.run(['quartus_sh', '-t', 'quartus_synth_script.tcl'], cwd=self.proj_dir, capture_output=True)
        subprocess.run(['quartus_syn', 'autoqpf'], cwd=self.proj_dir, capture_output=True)

class VivadoSynthesis(SynthesisTool):
    '''
    Use Vivado to synthesize a commit level synthesis project.

    Assumes Vivado executables are on the system path
    '''
    tool_name = 'vivado'
    synth_script_name = 'vivado_synth_script.tcl'
    success_msg = 'synth_design completed successfully'
    logfile_name = 'vivado.log'

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
        self.synth_script = [
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

    def _run_tool_wrapped(self):
        '''
        Run Vivado in headless mode to execute the synthscript in the commit
        level project directory. Assume Vivado is on the path.
        '''
        subprocess.run(['vivado', '-mode', 'tcl', '-source', self.synth_script_name], cwd=self.proj_dir, capture_output=True)

