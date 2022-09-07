## Essentially intended to be a way to create some nice stats plots for the paper
## July 2021-July 2022: 1807 candidates, average of 4.36 candidates per day

## Need to stylize the plots

from secrets import choice
import subprocess
import sys
import os
import argparse
import glob
import time

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

## argument for folder to run stats on
parser = argparse.ArgumentParser()
parser.add_argument("-c","--candDir", type=str, default=None, help="Path to the candidate directory")
parser.add_argument("-f","--fitDir", type=str, default=None, help="Path to the fits directory")
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-o', '--outdir', type=str, default=os.path.join('./outdir/stats/',time.strftime("%Y%m%d-%H%M%S"),''))
args = parser.parse_args()

# if not os.path.exists(args.outdir):
#         os.makedirs(args.outdir)
if args.candDir:
    dayList = glob.glob(args.candDir + "*")

    dayCount = [day for day in range(0,len(dayList))]

    numDaily = [len(glob.glob(day + "/*.csv")) for day in dayList]

    candList = glob.glob(args.candDir + "*/*.csv")

    cumDaily = np.cumsum(numDaily,axis=1)
else:
    print("No candidate directory specified, cannot run some stats")

def plotDir(name,ext=".png"):
    if not os.path.exists(args.outdir):
        os.makedirs(args.outdir)
    filepath = os.path.join(args.outdir,name,ext)
    return(filepath)

## plot the number of candidates per day
def plotDailyCand():
    plt.plot(dayCount, numDaily)
   #plt.xlabel("Day")
    plt.savefig(plotDir("numDailyCand"))

## plot the cumulative number of candidates per day
def plotCumDailyCand():
    plt.plot(dayCount,cumDaily)
   #plt.xlabel("Day")
    plt.savefig(plotDir("cumDailyCand"))

## plot the number of candidates per day with a rolling average
def plotDailyCandRolling():
    plt.plot(dayCount, numDaily)
    plt.plot(dayCount, pd.Series(numDaily).rolling(7).mean())
    plt.savefig(plotDir("numDailyCandRolling"))

## need to find way to plot time taken to run fits
## would be done using the fitDir argument and the .log files located in each fit directory


    

