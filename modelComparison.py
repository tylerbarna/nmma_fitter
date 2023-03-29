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
parser.add_argument("--candidate", type=str, help="Name of candidate")
parser.add_argument("--candDir", type=str, help="Path to candidate fits")
parser.add_argument("-m","--models", nargs="+", type=str, default = ["Bu2019lm", "nugent-hyper", "TrPi2018", "Piro2021"], help='which models to compare')
parser.add_argument('-o',"--outdir",type=str,default="./",help="Output directory")

args = parser.parse_args()

## retrieve data for each model, and plot to compare 
data_file = os.path.join(args.candDir,"candidate_data", args.candidate + ".dat")


plotdir = os.path.join(args.outdir, "plots")
if not os.path.isdir(plotdir):
    os.makedirs(plotdir, exist_ok=True)
    os.chmod(plotdir, 0o774)

## plot the original data
data_out = loadEvent(data_file)
filters = data_out.keys()
colors=cm.Spectral(np.linspace(0,1,len(filters)))[::-1]

trigger_time = 1
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
    
    ## now to plot all models listed (not ready yet)
    
    for model in args.models:
        # magKN_KNGRB_plot = getFilteredMag(bestfit_lightcurve_magKN_KNGRB, filt)

        # plt.plot(bestfit_lightcurve_magKN_KNGRB.bestfit_sample_times, magKN_KNGRB_plot, color=color2,linewidth=3, linestyle='--')
        # plt.fill_between(bestfit_lightcurve_magKN_KNGRB.bestfit_sample_times, magKN_KNGRB_plot + error_budget, magKN_KNGRB_plot - error_budget, facecolor=color2, alpha=0.2)

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