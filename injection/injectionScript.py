import subprocess
import sys
import os
import argparse
import json
import time

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import pickle

from astropy.time import Time

from json import dumps, loads, JSONEncoder, JSONDecoder

from matplotlib.pyplot import cm

from nmma.em.model import SVDLightCurveModel, GRBLightCurveModel, KilonovaGRBLightCurveModel, SupernovaGRBLightCurveModel
from nmma.em.utils import loadEvent, getFilteredMag

##Command Line Args for injection creation
parser = argparse.ArgumentParser(description="injection data lightcurve parameters")
parser.add_argument('--prior-file',type=str,required=True,help='prior file path for injection generation')
parser.add_argument('--eos-file',type=str,required=True,help="EOS file in (radius [km], mass [solar mass], lambda)")
parser.add_argument("-n", "--n-injection",type=int, default=None,help="The number of injections to generate: not required if --gps-file or injection file is also given (should be at least one for our purposes)")
parser.add_argument("--binary-type",type=str,required=True,help="Either BNS or NSBH")
parser.add_argument("--outfolder",type=str,help="generic output folder for all files")
#parser.add_argument("-f", "--filename",type=str,help="injection file output") ## could probably combine this and --outdir by making one argument for the base outdirectory and making injection.json the standard name
#parser.add_argument("-e", "--extension",type=str,default="dat",choices=["json", "dat"],help="Prior file format")

##Command line Args for lightcurve creation
##parser.add_argument("--injection",required=True,type=str,help="path to injection file")#Note:Redundant here
parser.add_argument("--model","-m",type=str,required=True,help="model type (currently using Bu2019lm)")
parser.add_argument("--label",type=str,required=True,help="output Label for lightcurve")
parser.add_argument("--svd-path", type=str,default='/panfs/roc/groups/7/cough052/shared/NMMA/svdmodels/',help="path to svd models folder")
parser.add_argument("--filters",type=str,default= "g,r,i",help="filters to use")
parser.add_argument("--injection-detection-limit",type=str,default= "22,22,22",help="detection limit for each filter")
#parser.add_argument("--outdir",type=str,default="./lightcurves/",help="output directory for lightcurves")
##misc Args
parser.add_argument("--cpus",type=int,default=1,help="number of cpus for lightcurve generation") ##Note: not working right now
parser.add_argument('--id-number',type=str,default="0",help='starting number for lightcurve ID column')
parser.add_argument('--tar','-t',action='store_true',help='automatically tar folder into local directory')
args = parser.parse_args()
#print(args)

job_id = os.environ["SLURM_JOB_ID"]
print('%s slurm job: %s' % (Time(time.time(),format='unix').isot, job_id))



##Creating injection from prior file


subprocess.run(' '.join(('mkdir -p',args.outfolder)),shell=True,capture_output=True)

injection_json = os.path.join(args.outfolder,'injection.json')

subprocess.run(' '.join(('cp',args.prior_file,os.path.join(args.outfolder,'prior.json'))),shell=True,capture_output=True)

activateNMMA = subprocess.run("conda activate nmma",shell=True,capture_output=True)

print('%s creating injection' % Time(time.time(),format='unix').isot)
injectionString = ' '.join((
"nmma_create_injection",
"--prior-file",str(args.prior_file),
"--eos-file",str(args.eos_file),
"--n-injection",str(args.n_injection),
"--binary-type",str(args.binary_type),
"-f",injection_json,
"--original-parameters"
))
injectionCommand = subprocess.run(injectionString,shell=True,capture_output=True)


##geocent_time workaround
print('%s doing geocent_time workaround' % Time(time.time(),format='unix').isot) 
with open(injection_json,"r") as file:
    json_object = json.load(file)

json_object['injections']["content"]['geocent_time_x'] = json_object['injections']["content"].get('geocent_time')
with open(injection_json,"w") as file:
    json.dump(json_object,file)


## Creating Lightcurves from Injection
## NOTE: light_curve_generation has been modified from the master branch to work for these purposes"
print('%s creating lightcurves' % Time(time.time(),format='unix').isot)
lc_path = os.path.join(args.outfolder,'lightcurves/')
lightcurveString = ' '.join((
"light_curve_generation",
"--injection" , injection_json,
"--label" , str(args.label),
"--model" , str(args.model),
"--svd-path" , str(args.svd_path),
"--filters" , str(args.filters),
"--injection-detection-limit" , str(args.injection_detection_limit),
"--outdir" , lc_path
))

lightcurveCommand = subprocess.run(lightcurveString,shell=True,capture_output=True)

print('%s combining lightcurves' % Time(time.time(),format='unix').isot)
combineString = ' '.join((
"python /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/lc_converter.py",
'--lc-directory',lc_path,
'--id-number',args.id_number,
'--outfile',os.path.join(args.outfolder,"lightcurves.csv")
))

combineCommand = subprocess.run(combineString,shell=True,capture_output=True)


print('%s lightcurve generation complete' % Time(time.time(),format='unix').isot)

for ext in ('.out','.err'):
    logPath = os.path.join('./logs',''.join((job_id,ext)))
    destLogPath = os.path.join(args.outfolder,''.join(('job',ext)))
    cpString = ' '.join((
    'cp',
    logPath,
    destLogPath
    ))
    cpCommand = subprocess.run(cpString, shell=True,capture_output=True)

if args.tar: ##not working, first line is being taken as noneType
    tar_name = ''.join((args.outfolder.split('/').remove('')[-1],'.tar.gz'))
    tarString = ' '.join((
    'tar -zcf',
    os.path.join('tars/',tar_name),
    args.outfolder
    ))
    tarCommand = subprocess.run(tarString,shell=True,capture_output=True)