## Note: This script is in no way generalized and was only created to manually plot one of the fits that was output when run 
## manually on a local machine. Will not work without significant modification
## Also, to my knowledge, it's fairly redundant now that nmma has a best fit plot flag

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

parser = argparse.ArgumentParser(description="Inference on kilonova ejecta parameters.")

parser.add_argument("--datafile", type=str,default='./candidate_data/paper_candidates/v1/candidate_data/ZTF21abotose.dat', help="Plotting Data")
parser.add_argument("--plotdir", type=str, default="./outdir", help="Directory to save plots")
parser.add_argument("--model", type=str, default="Piro2021", help="Model to use")
parser.add_argument("--svdpath", type=str, default="./svdmodels", help="Path to svd files")

parser.add_argument("--candname", type=str, default='ZTF21abotose', help="Name of the transient")
args = parser.parse_args()

svd_mag_ncoeff = 10
svd_lbol_ncoeff = 10
Ebv_max = 0.5724
grb_resolution = 7
jet_type = 0
joint_light_curve = False
sampler = 'pymultinest'
seed = 42
fit_trigger_time = True
error_budget = 1.0

trigger_time=59422.318

candname = args.candname
model = args.model
svd_path = args.svdpath

plotdir = os.path.join("./",candname)
if not os.path.isdir(plotdir):
    os.makedirs(plotdir, exist_ok=True)

##############################
# Construct the best fit model
##############################

plot_sample_times = np.arange(0.01, 10.21, 0.1)
if model == "TrPi2018" or model == "nugent-hyper":
    plot_sample_times = np.arange(0.01, 10.21, 0.2)

posterior_file = os.path.join('./outdir/ZTF21abotose_posterior_samples.dat')
bestfit_params, bestfit_lightcurve_magKN_KNGRB = get_bestfit_lightcurve(model, posterior_file, svd_path,\
                                                                        plot_sample_times,\
                                                                        grb_resolution = grb_resolution,\
                                                                        joint_light_curve = joint_light_curve)

if fit_trigger_time:
    trigger_time += bestfit_params['KNtimeshift']


#######################
# Plot the lightcurves
#######################
data_file = './candidate_data/paper_candidates/v1/candidate_data/ZTF21abotose.dat'
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