set outputdir autosynthxpr
set project autosynth
set partnumber xcvu3p-ffvc1517-3-e

file mkdir $outputdir

create_project -part $partnumber $project $outputdir

add_files [lindex $argv 0]

synth_design -top [lindex $argv 1]

exit
