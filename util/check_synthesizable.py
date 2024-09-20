import subprocess
import os
import shutil

def run_vivado_synth(name, top):
	'''
	Synthesize the HDL located in name, with the top module as top, using
	Vivado.

	Assumes vivado is on the path, and uses `vivado_synth.tcl` to run
	synthesis.

	returns True if synthesis was successful
	'''

	# This message should turn up in the log to indicate successful synthesis
	success_msg = 'synth_design completed successfully'

	# The directories and files we expect Vivado to produce
	projdir = 'autosynthxpr'
	journalfile = 'vivado.jou'
	logfile = 'vivado.log'

	# run vivado, and surpress the output
	subprocess.run(['vivado', '-mode', 'tcl', '-source', 'vivado_synth.tcl', '-tclargs', name, top], capture_output=True)

	# ensure that vivado ran properly and bailout other wise
	xpr_exists = os.path.isdir(projdir)
	journal_exists = os.path.isfile(journalfile)
	log_exists = os.path.isfile(logfile)
	if not (xpr_exists and journal_exists and log_exists):
		print("FAILED: Seems like Vivado did not run.")
		exit()

	# read the log to see if synthesis was successful
	with open(logfile, 'r') as vlog:
		synth_result = vlog.readlines()

	success = False
	for line in synth_result:
		if success_msg in line:
			success = True

	# clean up vivado project
	shutil.rmtree(projdir)
	os.remove(journalfile)
	os.remove(logfile)

	return success

def get_sha(name):
	'''
	Get the SHA of HEAD in the repo `name`

	returns the SHA as a string
	'''
	sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=name, capture_output=True)
	sha = sha.stdout.decode('utf8').replace('\n','')
	return sha

def step_back_one_commit(name):
	'''
	Step HEAD back one commit in the repo `name`

	returns false if end of history was detected, true otherwise
	'''
	# the message we expect if we hit the oldest commit
	end_of_hist = "error: pathspec 'HEAD~1' did not match any file(s) known to git."

	# attempt to step back one commit
	msg = subprocess.run(['git', 'checkout', 'HEAD~1'], cwd=name, capture_output=True)
	msg = msg.stderr.decode('utf8').replace('\n','n')

	# check to see if we hit oldest commit
	if end_of_hist in msg:
		return False
	else:
		return True

def main():
	name = os.path.join('..','corundum')
	top = 'mqnic_core_pcie'
	commit_depth = 5

	for _ in range(commit_depth):
		synth_result = run_vivado_synth(name, top)
		sha = get_sha(name)

		if synth_result:
			print(sha + " Synthesizable")
		else:
			print(sha + " Unsynthesizable")

		stepped = step_back_one_commit(name)
		if not stepped:
			print("QUITTING: reached end of history")
			exit()

if __name__ == '__main__':
	main()
