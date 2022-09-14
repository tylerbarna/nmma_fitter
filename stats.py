## Essentially intended to be a way to create some nice stats plots for the paper
## July 2021-July 2022: 1807 candidates, average of 4.36 candidates per day

## Need to stylize the plots; could define a function to outline a consistent plot style and size depending on plot type to reduce repetition

from secrets import choice
import subprocess
import sys
import os
import argparse
import glob
import time
import json

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
parser.add_argument("-m","--models", nargs="+", type=str, default = ["TrPi2018","nugent-hyper", "Piro2021","Bu2019lm"], choices = ["TrPi2018","nugent-hyper", "Piro2021","Bu2019lm"], help="which models to analyse with the fit stats")
args = parser.parse_args()

# if not os.path.exists(args.outdir):
#         os.makedirs(args.outdir)
if args.candDir:
    dayList = glob.glob(os.path.join(args.candDir, "/*/"))

    dayCount = [day for day in range(0,len(dayList))]

    numDaily = [len(glob.glob(day + "/*.csv")) for day in dayList]

    candList = glob.glob(args.candDir + "*/*.csv")

    cumDaily = np.cumsum(numDaily,axis=1)
else:
    print("No candidate directory specified, cannot run some stats")

if args.fitDir:
    fit_dayList = glob.glob(args.fitDir + "*")
    
    ## attempted dict comprehension for finding all instances of logs
    logDict = {model: glob.glob(os.path.join(args.fitDir,'*',model+'.log')) for model in args.models}
    jsonDict = {model: glob.glob(os.path.join(args.fitDir,'*',model+'_result.json')) for model in args.models}

else:
    print("No candidate directory specified, cannot run some stats")


## Candidate Directory stats

def plotDir(name,outdir=args.outdir,ext=".png",):
    '''check for existence of plot directory and create if needed, then return full path for saving figure'''
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    filepath = os.path.join(outdir,name+ext)
    return(filepath)


def plotDailyCand():
    '''plot the number of candidates per day'''
    plt.plot(dayCount, numDaily)
    plt.xlabel("Days Since Start") ## weird phrasing
    plt.ylabel('Number of Daily Candidates')
    plt.savefig(plotDir("numDailyCand"))


def plotCumDailyCand():
    '''plot the cumulative number of candidates per day'''
    plt.plot(dayCount,cumDaily)
    plt.xlabel("Days Since Start")
    plt.ylabel('Cumulative Number of Candidates')
    plt.savefig(plotDir("cumDailyCand"))


def plotDailyCandRolling():
    '''plot the number of candidates per day with a rolling average'''
    plt.plot(dayCount, numDaily)
    plt.plot(dayCount, pd.Series(numDaily).rolling(7).mean())
    plt.savefig(plotDir("numDailyCandRolling"))



## Fit Directory Stats

## need to find way to plot time taken to run fits
## would be done using the fitDir argument and the .log files located in each fit directory

def get_sampling_time(file=None):
    '''pulls from the provided json file to find the sampling_time and returns that value. sampling_time is recorded in seconds'''
    if file:
        with open(file) as f:
            try: 
                data = json.load(f)
                sampling_time = data['sampling_time']
            finally:
                f.close()
                return sampling_time
    else:
        print('provide a file to search!')
        exit(1)

def countDailyFits(day=None, models=args.models): ##relying on args as default might not be the best idea
    '''finds how many fits were completed on a given day, with day being provided as a path string'''
    if day:
        fitCands = glob.glob(os.path.join(day,'*/')) ## will return the paths to the candidates that were fit + the candidate_data folder 
        if os.path.join(day,'candidate_data/') in fitCands:
            candList = glob.glob(os.path.join(day,'candidate_data','*.dat'))
            numCands = len(candList) ## tp compare number of fit candidates to number of submitted
            fitCands.remove(os.path.join(day,'candidate_data/')) ## might be unnecessary
        else:
            numCands = len(fitCands)
        
        ## count number of fits completed for each model
        numFits = {model: len(os.path.join(day,'*',model+'_result.json')) for model in models}
        sumFits = sum(numFits.values())
        ## count number of candidates that weren't fit
        numUnfit = numCands - len(fitCands) 

        return {
        'fitCands': fitCands,
        'numCands':numCands, 
        'numFits':numFits, 
        'sumFits':sumFits, 
        'numUnfit':numUnfit
        }
    else:
        print('provide a day to count fits for!')
        exit(1)



## find a way to plot each model's cumulative 

def plotModelCum(models=args.models, save=True):
    '''plot the cumulative number of fits for each model'''
    ## modelDict creates dict of cumulative fit counts for each model so they can be plotted together
    modelDict = {}
    ## Potential alternate option: plot them all on the same plot as subplots
    for model in models: ## get cumulative number of fits for each model, plot, save, and add to modelDict
        ##
        ## compile cumulative number of fits for each model
        modelCount = [len((glob.glob(os.path.join(day,'*',model+'_result.json')))) for day in fit_dayList]
        modelCum = np.cumsum(modelCount)
        modelDict[model] = modelCum
        
        plt.plot(dayCount,modelCum)
        plt.xlabel("Days Since Start")
        plt.ylabel('Count')
        plt.title('Cumulative Number of Fits for {}'.format(model))
        plt.savefig(plotDir("cumDailyFits_"+model)) if save else plt.clf()
        plt.clf()

    ## now plot all models together
    for key, value in modelDict.items(): 
        
        plt.plot(dayCount,modelCum, label=key, marker='o')
        plt.xlabel("Days Since Start")
        plt.ylabel('Count')
        ## need to cmap or something for controlling colors
    plt.title('Cumulative Number of Fits for All Models')
    plt.legend()
    plt.savefig(plotDir("cumDailyFits_all")) if save else plt.clf()
    plt.clf()
    return modelDict ## maybe not necessary to return this
    

## To Do:

## plot number of unfit candidates per day

## plot cumulative number of unfit candidates

## plot number of fits per day

## plot number of fits per day for each model

## plot amount of time taken to run fits per day per model

## plot total amount of time taken to run fits per day

## plot cumulative amount of time taken to run fits

## plot rolling average of each model fit time

## add a file size counter and plotter potentially