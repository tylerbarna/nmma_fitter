import subprocess
import sys
import os
import argparse

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




# Command line args
parser = argparse.ArgumentParser(description="Inference on kilonova ejecta parameters.")
parser.add_argument("--datafile", type=str, required=True, help="Path of the transient csv file")
parser.add_argument("--candname", type=str, required=True, help="Name of the transient")
parser.add_argument("--model", type=str, default='Bu2019lm', help="Name of the kilonova model to be used")
parser.add_argument("--nlive", type=int, default=256, help="Number of live points to use")
parser.add_argument("--cpus", type=int, default=2, help="Number of cpus to use")
parser.add_argument("-d","--dataDir", type=str, default=None)
args = parser.parse_args()

# Trigger time settings
# t0 is used as the trigger time if both fit and heuristic are false.
# Heuristic makes the trigger time 24hours before first detection.
t0 = 1
trigger_time_heuristic = False
fit_trigger_time = True

# Will select prior file if None
# Can be assigned a filename to be used instead
prior = None

#extract candidate name from the data file name
candname = args.candname

# Load the data. Depends on the data format. 
# Also saves a file in NMMA's format
nmma_data = parse_csv(args.datafile, candname)

# -TODO- parse_csv need not return the data if nmma loads it later?

# Other important settings
model = args.model 
svd_path = '/home/cough052/shared/NMMA/svdmodels'

# outdir mess
## Need to update so it checks an argument to choose latest_directory
os.chdir("/panfs/roc/groups/7/cough052/shared/ztfrest/candidate_fits")
candidate_directory = "/panfs/roc/groups/7/cough052/shared/ztfrest/candidates/partnership"
#if args.dataDir == "None": ## Hacky band-aid, probably unneeded 
    #latest_directory = max([f for f in os.listdir(candidate_directory)], key=lambda x: os.stat(os.path.join(candidate_directory,x)).st_mtime)
    #print("Using manual folder %s" % latest_directory)
if args.dataDir:
    latest_directory = args.dataDir
    #print("Using manual folder %s" % latest_directory)
elif not args.dataDir:
    latest_directory = max([f for f in os.listdir(candidate_directory)], key=lambda x: os.stat(os.path.join(candidate_directory,x)).st_mtime)
    #print("Using most recent directory %s" % latest_directory)

outdir = os.path.join("./",latest_directory,"") 
if not os.path.isdir(outdir):
    os.makedirs(outdir, exist_ok=True)
os.chdir(outdir)

cpus = args.cpus
nlive = args.nlive
error_budget = 1.0

##########################
# Setup parameters and fit
##########################

#label = candname + "_" + model
label = model 
data_file = "./candidate_data/" + candname + ".dat"

# Set the trigger time
if fit_trigger_time:
    # Set to earliest detection in preparation for fit
    for line in nmma_data:
        if np.isinf(float(line[3])):
            continue
        else:
            trigger_time = Time(line[0], format='isot').mjd
            break
elif trigger_time_heuristic:
    # One day before the first non-zero point
    for line in nmma_data:
        if np.isinf(float(line[3])):
            continue
        else:
            trigger_time = Time(line[0], format='isot').mjd - 1
            break
else:
    # Set the trigger time
    trigger_time = t0

tmin = 0
tmax = 7
dt = 0.1
# GRB model requires special values so lightcurves can be generated without NMMA running into timeout errors.
if model == "TrPi2018" or model == "nugent-hyper":
    tmin = 0.01
    tmax = 7.01
    dt = 0.35

svd_mag_ncoeff = 10
svd_lbol_ncoeff = 10
Ebv_max = 0.5724
grb_resolution = 7
jet_type = 0
joint_light_curve = False
sampler = 'pymultinest'
seed = 42

if model == "nugent-hyper":
    joint_light_curve = True

#if not os.path.isdir(outdir):
    #os.makedirs(outdir)
    #os.chmod(outdir, 0o774)

plotdir = os.path.join("./",candname)
if not os.path.isdir(plotdir):
    os.makedirs(plotdir, exist_ok=True)
    os.chmod(plotdir, 0o774)

# Set the prior file. Depends on model and if trigger time is a parameter.
if prior == None:
    if joint_light_curve:
        if model != 'nugent-hyper':
            #KN+GRB
            print("Not yet configured for KN+GRB")
            quit()
        else:
            #supernova
            if fit_trigger_time:
                prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/ZTF_sn_t0.prior'
            else:
                prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/ZTF_sn.prior'
    else:
        if model == 'TrPi2018':
            # GRB
            if fit_trigger_time:
                prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/ZTF_grb_t0.prior'
            else:
                prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/ZTF_grb.prior'
        else:
            # KN
            if fit_trigger_time:
                prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/ZTF_kn_t0.prior'
            else:
                prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/ZTF_kn.prior'

# NMMA lightcurve fitting
# triggered with a shell command
command_string = "mpiexec -np " + str(cpus) + " light_curve_analysis"\
    + " --model " + model + " --svd-path " + svd_path + " --outdir " + plotdir\
    + " --label " + model + " --trigger-time " + str(trigger_time)\
    + " --data " + data_file + " --prior " + prior + " --tmin " + str(tmin)\
    + " --tmax " + str(tmax) + " --dt " + str(dt) + " --error-budget " + str(error_budget)\
    + " --nlive " + str(nlive) + " --Ebv-max " + str(Ebv_max)+\
    " --detection-limit \"{\'r\':21.5, \'g\':21.5, \'i\':21.5}\""

if joint_light_curve:
    command_string += " --joint-light-curve"

command = subprocess.run(command_string, shell=True, capture_output=True)
sys.stdout.buffer.write(command.stdout)
sys.stderr.buffer.write(command.stderr)

##############################
# Construct the best fit model
##############################

plot_sample_times = np.arange(0.01, 10.21, 0.1)
if model == "TrPi2018" or model == "nugent-hyper":
    plot_sample_times = np.arange(0.01, 10.21, 0.2)

posterior_file = os.path.join(plotdir, model + '_posterior_samples.dat')
bestfit_params, bestfit_lightcurve_magKN_KNGRB = get_bestfit_lightcurve(model, posterior_file, svd_path,\
                                                                        plot_sample_times,\
                                                                        grb_resolution = grb_resolution,\
                                                                        joint_light_curve = joint_light_curve)

if fit_trigger_time:
    trigger_time += bestfit_params['KNtimeshift']

# Can also fetch the log-likelihood from the bestfit_params
# bestfit_params['log_likelihood']

#######################
# Plot the lightcurves
#######################

# Load the data for plotting
data_out = loadEvent(data_file)
filters = data_out.keys()

color2 = 'coral'
color1 = 'cornflowerblue'

colors=cm.Spectral(np.linspace(0,1,len(filters)))[::-1]

plotName = os.path.join(plotdir, model + '_lightcurves.png')
plt.figure(figsize=(20,28))

cnt = 0
for filt, color in zip(filters,colors):
    cnt = cnt+1
    if cnt == 1:
        ax1 = plt.subplot(len(filters),1,cnt)
    else:
        ax2 = plt.subplot(len(filters),1,cnt,sharex=ax1,sharey=ax1)

    if not filt in data_out: 
        continue
    samples = data_out[filt]
    t, y, sigma_y = samples[:,0], samples[:,1], samples[:,2]
    t -= trigger_time
    idx = np.where(~np.isnan(y))[0]
    t, y, sigma_y = t[idx], y[idx], sigma_y[idx]
    if len(t) == 0: 
        continue

    idx = np.where(np.isfinite(sigma_y))[0]
    plt.errorbar(t[idx],y[idx],sigma_y[idx],fmt='o',color='k', markersize=16, label='%s-band'%filt) # or color=color

    idx = np.where(~np.isfinite(sigma_y))[0]
    plt.errorbar(t[idx],y[idx],sigma_y[idx],fmt='v',color='k', markersize=16) # or color=color

    magKN_KNGRB_plot = getFilteredMag(bestfit_lightcurve_magKN_KNGRB, filt)

    plt.plot(bestfit_lightcurve_magKN_KNGRB.bestfit_sample_times, magKN_KNGRB_plot, color=color2,linewidth=3, linestyle='--')
    plt.fill_between(bestfit_lightcurve_magKN_KNGRB.bestfit_sample_times, magKN_KNGRB_plot + error_budget, magKN_KNGRB_plot - error_budget, facecolor=color2, alpha=0.2)

    plt.ylabel('%s'%filt,fontsize=48,rotation=0,labelpad=40)

    plt.xlim([0.0, 10.0])
    plt.ylim([26.0,14.0])
    plt.grid()

    if cnt == 1 and cnt == len(filters):
        ax1.set_yticks([26,24,22,20,18,16,14])
        ax1.set_xticks(range(0,11))
        plt.setp(ax1.get_xticklabels(), visible=True)
    elif cnt == 1:
        ax1.set_yticks([26,24,22,20,18,16,14])
        ax1.set_xticks(range(0,11))
        plt.setp(ax1.get_xticklabels(), visible=False)
        #l = plt.legend(loc="upper right",prop={'size':36},numpoints=1,shadow=True, fancybox=True)
    elif not cnt == len(filters):
        plt.setp(ax2.get_xticklabels(), visible=False)
    plt.xticks(fontsize=36)
    plt.yticks(fontsize=36)

ax1.set_zorder(1)
plt.xlabel('Time [days]',fontsize=48)
plt.tight_layout()
plt.savefig(plotName)
plt.close()

subprocess.run(["chmod","774","-R",plotdir])

# File to indicate fit is complete
completefile = os.path.join('.', candname + "_" + model + '.fin')
file = open(completefile, "w") 
file.close()
