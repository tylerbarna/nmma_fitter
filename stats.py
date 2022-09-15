## Essentially intended to be a way to create some nice stats plots for the paper
## July 2021-July 2022: 1807 candidates, average of 4.36 candidates per day

## Need to stylize the plots; could define a function to outline a consistent plot style and size depending on plot type to reduce repetition
## need to fig,ax stuff

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

## compilation of lists for use in plotting (pre-dataframe implementation)
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
    ## the way these are written, it may have issues for plotting if some days don't have all models
else:
    print("No candidate directory specified, cannot run some stats")


## Utility functions

def plotDir(name,outdir=args.outdir,ext=".png",):
    '''
    check for existence of plot directory and create if needed, then return full path for saving figure
    
    Args:
    name: name of the plot for the filename (without extension)
    outdir: path to the output directory
    ext: extension of the plot file (typically .png or .pdf)
    '''
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    filepath = os.path.join(outdir,name+ext)
    return(filepath)


def get_sampling_time(file=None): ## somewhat redundant after creation of get_json
    '''
    Pulls from the provided json file to find the sampling_time and returns that value. sampling_time is recorded in seconds
    
    Args:
    file: path to the json file to be parsed
    '''
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
        exit(1) ## irreconciable error, hence exit(1)


def get_json(file=None, params=None): ## effectively an improvement on get_sampling_time so it provides more flexibility and can be used for other parameters
    '''
    pulls from the provided json file to find several values and returns them in a dictionary. sampling_time is recorded in seconds. NOTE: all values are returned as strings and must be converted to the appropriate type when used.

    Args:
    file: path to json file (required). Taken as path string, but will also accept boolean False to return dictionary populated by np.nan values.
    params: list of additional parameters to pull from json file.
    '''
    jsonList = ['sampling_time', 'sampler', 'log_evidence','log_evidence_err', 'log_noise_evidence',  'log_bayes_factor']
    if params:
        jsonList = jsonList + params
    if file:
        with open(file) as f:
            try: 
                data = json.load(f)
                jsonDict = {param: data[param] for param in jsonList}
            finally:
                f.close()
                return jsonDict
    elif not file: ## for use case where no json is found when the pandas dataframe is created
        jsonDict = {param: np.nan for param in jsonList} ## np.nan is used to make it easier to plot later without having to deal with NoneType
        return jsonDict
    else: ## case where file argument is not provided
        print('provide a file to search!')
        exit(1) ## irreconciable error, hence exit(1)


def countDailyFits(day=None, models=args.models): ##relying on args as default might not be the best idea
    '''
    finds how many fits were completed on a given day, with day being provided as a path string
    
    Args:
    day: path to day directory
    models: list of models to search for
    '''
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
        exit(1) ## irreconciable error, hence exit(1)


def get_dataframe(candDir=args.candDir, fitDir=args.fitDir, models=args.models, save=True, file=None):
    '''
    Creates or loads in a pandas dataframe with relevant values for different candidates. If a file is provided, the dataframe will be loaded from that file. Otherwise, the dataframe will be created from the candidate and fit directories provided. 

    Args:
    candDir: path to candidate directory
    fitDir: path to fit directory
    save: boolean to determine whether to save the dataframe to a file to be accessed later
    file: path of saved dataframe to be read in. If None, will proceed to generate dataframe
    '''
    if file:
        df = pd.read_csv(file) ## needs to be tested to ensure compatibility with saved dataframe
        return df
    
    df = pd.DataFrame()
    idx = 0 ## used to keep track of the index of the dataframe when defining new values
    dayPathList = glob.glob(os.path.join(candDir, "/*/"))
    dayList = [dayPath.split('/')[-2] for dayPath in dayPathList]
    for day, dayPath in zip(dayList, dayPathList):
        ## get lists for day level directories
        candPathList = glob.glob(os.path.join(dayPath, "*.csv")) ## could change to have a .dat argument option
        candList = [cand.split('/')[-1].split('.')[0].split('_')[1] for cand in candPathList] ## this is a bit of a mess, but it works (hopefully)
        for cand, candPath in zip(candList, candPathList):
            ## search for models at same time as candidate data
            for model in models:
                df.at[idx, 'day'] = day
                df.at[idx, 'dayPath'] = dayPath
                df.at[idx, 'cand'] = cand
                df.at[idx, 'candPath'] = candPath
                df.at[idx, 'model'] = model

                ## check if fit was completed
                fitPath = os.path.join(fitDir, day, cand,"")
                df.at[idx, 'fitPath'] = fitPath
                ## now find json
                jsonPath = os.path.join(fitPath, model+'_result.json')
                if jsonPath:
                    df.at[idx, 'json'] = jsonPath
                    df.at[idx, 'fitBool'] = True
                    ## now get values from json
                    jsonDict = get_json(file=jsonPath[0])
                    for key, value in jsonDict.items():
                        df.at[idx, key] = value
                elif not jsonPath:
                    df.at[idx, 'json'] = np.nan
                    df.at[idx, 'fitBool'] = False
                    ## now get values from json
                    jsonDict = get_json(file=False)
                    for key, value in jsonDict.items():
                        df.at[idx, key] = value ## should be np.nan
                idx += 1
    if save:
        df.to_csv(plotDir(name='statsDataframe',ext='.csv')) ## Not exactly the intended use of plotDir, but it works (probably)
    return df




## Functions to plot daily candidate stats

def plotDailyCand(save=True):
    '''
    plot the number of candidates per day as both a line plot and histogram
    
    Args:
    save: boolean to determine whether to save the plot or not
    '''
    plt.plot(dayCount, numDaily,marker='o')
    plt.xlabel("Days Since Start") ## weird phrasing
    plt.ylabel('Number of Daily Candidates')
    plt.savefig(plotDir("numDailyCand")) if save else plt.clf()
    plt.clf()
    ## plot histogram of number of candidates per day
    plt.hist(numDaily, bins=20) ## could fine tune the number of bins
    plt.xlabel("Number of Candidates per Day")
    plt.ylabel('Count')
    plt.savefig(plotDir("numDailyCandHist")) if save else plt.clf()



def plotCumDailyCand(save=True): ## could switch to seaborn to make smoother/prettier curve
    '''
    Plot the cumulative number of candidates per day
    
    Args:
    save: boolean to determine whether to save the plot or not
    '''
    plt.plot(dayCount,cumDaily)
    plt.xlabel("Days Since Start")
    plt.ylabel('Cumulative Number of Candidates')
    plt.savefig(plotDir("cumDailyCand")) if save else plt.clf()


def plotDailyCandRolling(save=True):
    '''
    Plot the number of candidates per day with a rolling average
    
    Args:
    save: boolean to determine whether to save the plot or not
    '''
    plt.plot(dayCount, numDaily)
    plt.plot(dayCount, pd.Series(numDaily).rolling(7).mean())
    plt.xlabel("Days Since Start")
    plt.ylabel('Number of Daily Candidates')
    plt.savefig(plotDir("numDailyCandRolling")) if save else plt.clf()




## Functions to plot fitting stats

## need to find way to plot time taken to run fits
## would be done using the fitDir argument and the .log files located in each fit directory
## find a way to plot each model's cumulative 

def plotFitCum(models=args.models, save=True):
    '''
    plot the cumulative number of fits for each model
    
    Args:
    models: list of models to search for
    save: boolean to determine whether to save the figure or not
    '''
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
    try: ## using a try here because this could totally break if the modelDict has different lengths for each model
        modelDict['total'] = sum(map(np.array,modelDict.values())).tolist()
    except:
        print('Keys in modelDict probably do not have the same length')
        pass
    ## now plot all models together
    for key, value in modelDict.items(): 
        plt.plot(dayCount,value, label=key, marker='o')
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

## plot amount of time taken to run fits per day per model

## plot total amount of time taken to run fits per day

## plot cumulative amount of time taken to run fits

## plot rolling average of each model fit time

## add a file size counter and plotter potentially

## plot histogram of 