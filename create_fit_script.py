import argparse
import json
import os
import subprocess
import sys

## goal of this would be to generate the job script using the settings.json file and then delete it after the job is submitted

parser = argparse.ArgumentParser()
parser.add_argument("-m","--model",type=str,default=None)
parser.add_argument("-t","--fit_trigger_time",action="store_true")
args = parser.parse_args()

model = args.model



config = json.load(open('settings.json'))
job_config = config['models'][model]['job']
job_settings = config['settings']

## maybe make the job name more descriptive? or so it doesn't overwrite an existing job if it hasn't been submitted yet
f = open('job.sh','a')

f.write('#!/bin/bash'+'\n')
f.write('#SBATCH --time='+job_config['time']+'\n')
f.write("#SBATCH --mail-type=ALL"+"\n")
f.write('#SBATCH --mail-user=ztfrest@gmail.com'+'\n')
f.write('#SBATCH --nodes='+job_config['nodes']+'\n')
f.write('#SBATCH --ntasks='+job_config['ntasks']+'\n')
f.write('#SBATCH --cpus-per-task='+job_config['cpus-per-task']+'\n')
f.write('#SBATCH --mem='+job_config['mem']+'\n')
f.write('#SBATCH -p '+job_config['partition']+'\n') 
f.write('#SBATCH -o %j.out'+'\n')
f.write('#SBATCH -e %j.err'+'\n')

f.write('\n')

f.write('source '+job_settings['env']['path']+' '+job_settings['env']['name']+'\n')

f.write('\n')


## this is where we run into a slight issue - the python script directory is specific to the user/system, so we would either need to add a line to the settings.json file to specify the path to the python script or some other way

## want to have it write something like
# python /panfs/roc/groups/7/cough052/barna314/nmma_fitter/nmma_fit.py --datafile "$1" --candname "$2" --model "$3" --dataDir "$4" --nlive 128 --cpus 4
