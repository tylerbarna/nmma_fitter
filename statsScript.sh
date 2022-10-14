#! /bin/bash
exec > statsTest/logfile.txt 2>&1
source /home/tbarna/anaconda3/bin/activate nmma
cd /home/tbarna/nmma_fitter
python3 ./stats.py -c ./candidate_data/pipelineStructureExample/candidates/partnership -f  ./candidate_data/pipelineStructureExample/candidate_fits -o ./statsTest --verbose