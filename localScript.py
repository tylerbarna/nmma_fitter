import subprocess
import sys
import os
import argparse
import glob

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from astropy.time import Time
 
from fit_utils import get_bestfit_lightcurve, parse_csv
from astropy.time import Time

from nmma.em.model import SVDLightCurveModel, GRBLightCurveModel, KilonovaGRBLightCurveModel, SupernovaGRBLightCurveModel
from nmma.em.utils import loadEvent, getFilteredMag

import seaborn as sns

## Goal of this script is to manually execute model fits of specific csv files and save the results to a folder.

parser = argparse.ArgumentParser()
parser.add_argument("-d","--dataDir", type=str, default=None)

## Currently not in use: allows for manual fitting of a specific candidate or candidates 
parser.add_argument("-c","--candidate", nargs="+", type=str, default=None)


## Would have to pass args.models as model_list when submitting jobs
## Would have to pass when executing fit bot as " ".join(f'"{m}"' for m in args.models)
parser.add_argument("-m","--models", nargs="+", type=str, default = ["TrPi2018","nugent-hyper", "Piro2021","Bu2019lm"])



parser.add_argument("--svdmodels", type=str, default="/home/cough052/shared/NMMA/svdmodels", help="Path to the SVD models. Note: Not present in the repo, need to be aquired separately (Files are very large)")
parser.add_argument("--nlive", type=int, default=256, help="Number of live points to use")


## where to output plots
parser.add_argument('-o',"--outdir",type=str,default='./outdir/')

args = parser.parse_args()

og_directory = os.getcwd()
outdir = args.outdir
svd_path = args.svdmodels

if not args.dataDir or args.candidate:
    print("Please pass --dataDir (-d) and/or --candidate (-c)")
    sys.exit()


if not args.models:
    print("No --models argument: Fitting to all models")

model_list = args.models

# job_name = {"Bu2019lm": "KNjob.txt",
#             "TrPi2018": "GRBjob.txt",
#             "nugent-hyper": "SNjob.txt",
#             "Piro2021": "SCjob.txt",}


if not os.path.exists(outdir):
    os.makedirs(outdir)

## No check on the number of detections, making assumption that all submissions have a requisite number of detections since this is a manually executed script



if args.dataDir:
    lc_data = glob.glob(args.dataDir+'*.dat', recursive=False)
elif args.candidate:
    lc_data = [args.candidate]

## assumes working with .dat files already (see nmma_fit.py for how those are found)
## could probably add that here so this is fully independent of nmma_fit being done

## Random Stuff from nmma_fit.py



svd_mag_ncoeff = 10
svd_lbol_ncoeff = 10
Ebv_max = 0.5724
grb_resolution = 7
jet_type = 0
joint_light_curve = False
sampler = 'pymultinest'
seed = 42

nlive = args.nlive
error_budget = 1.0

t0 = 1
trigger_time_heuristic = False
fit_trigger_time = True

for cand in lc_data: ## hacky way of doing things
    print(cand)
    candName = cand.split("/")[-1].split(".")[0]
    candDir = os.path.join(outdir,candName,"")
    if not os.path.exists(candDir):
        os.makedirs(candDir)
    
    candTable = pd.read_table(cand,delimiter=r'\s+', header=None)
    
    for model in model_list: 
        tmin = 0.01
        tmax = 7.01
        dt = 0.1

        # GRB model requires special values so lightcurves can be generated without NMMA running into timeout errors.
        if model == "TrPi2018":
            tmin = 0.01
            tmax = 7.01
            dt = 0.35
        
        if model == 'nugent-hyper':
            # SN
            if fit_trigger_time:
                prior = './priors/ZTF_sn_t0.prior'
            else:
                prior = './priors/ZTF_sn.prior'
        elif model == 'TrPi2018':
            # GRB
            if fit_trigger_time:
                prior = './priors/ZTF_grb_t0.prior'
            else:
                prior = './priors/ZTF_grb.prior'
        elif model == 'Piro2021':
            # Shock cooling
            if fit_trigger_time:
                prior = './priors/ZTF_sc_t0.prior'
            else:
                prior = './priors/ZTF_sc.prior'
        elif model == 'Bu2019lm':
            # KN
            if fit_trigger_time:
                prior = './priors/ZTF_kn_t0.prior'
            else:
                prior = './priors/ZTF_kn.prior'
        else:
            print("nmma_fitter does not know of the prior file for model "+ model)
            exit(1)

        if fit_trigger_time:
        # Set to earliest detection in preparation for fit
        # Need to search the whole file since they are not always ordered.
            trigger_time = np.inf
            for index, row in candTable.iterrows():
                if np.isinf(float(row[3])):
                    continue
                elif Time(row[0], format='isot').mjd < trigger_time:
                    trigger_time = Time(row[0], format='isot').mjd
        elif trigger_time_heuristic:
            # One day before the first non-zero point
            trigger_time = np.inf
            for index, row in candTable.iterrows():
                if np.isinf(float(row[3])):
                    continue
                elif (Time(row[0], format='isot').mjd - 1) < trigger_time:
                    trigger_time = Time(row[0], format='isot').mjd - 1
        else:
            # Set the trigger time
            trigger_time = t0

        print(trigger_time)

        command_string = " light_curve_analysis"\
        + " --model " + model + " --svd-path " + svd_path + " --outdir " + candDir\
        + " --label " + str(candName+"_"+model+"_nlive"+str(nlive))\
        + " --trigger-time " + str(trigger_time)\
        + " --data " + cand + " --prior " + prior + " --tmin " + str(tmin)\
        + " --tmax " + str(tmax) + " --dt " + str(dt) + " --error-budget " + str(error_budget)\
        + " --nlive " + str(nlive) + " --Ebv-max " + str(Ebv_max)\
        + " --detection-limit" +" \"{\'r\':21.5, \'g\':21.5, \'i\':21.5}\""\
        + " --plot"\
        + " --sampler dynesty" + " --verbose"

        command = subprocess.run(command_string, shell=True, capture_output=True)
        sys.stdout.buffer.write(command.stdout)
        sys.stderr.buffer.write(command.stderr)