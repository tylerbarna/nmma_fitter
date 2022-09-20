## Essentially intended to be a way to create some nice stats plots for the paper
## July 2021-July 2022: 1807 candidates, average of 4.36 candidates per day

## Need to stylize the plots; could define a function to outline a consistent plot style and size depending on plot type to reduce repetition - see https://stackoverflow.com/questions/51711438/matplotlib-how-to-edit-the-same-plot-with-different-functions and https://matplotlib.org/1.5.3/users/style_sheets.html for more info
## need to fig,ax stuff

## could probably consolidate some of the plotting functions into one function for each topic (e.g. one function for plotting the number of fits, one for plotting the number of unfit, etc.)

## alternatively, could change these into methods of a class that takes the dataframe as the object (e.g. df.plotDailyCand() ) 

# from secrets import choice
# import subprocess
# import sys
import os
import argparse
import glob
import time
import json

import numpy as np
import pandas as pd
# import matplotlib
import matplotlib.pyplot as plt
# from matplotlib.pyplot import cm
# from astropy.time import Time
 
# from fit_utils import get_bestfit_lightcurve, parse_csv
# from astropy.time import Time

# from nmma.em.model import SVDLightCurveModel, GRBLightCurveModel, KilonovaGRBLightCurveModel, SupernovaGRBLightCurveModel
# from nmma.em.utils import loadEvent, getFilteredMag

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
## post dataframe implementation: these should eventually be removed and plots should be updated to use the dataframe
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

def plotDir(name,outdir=args.outdir,ext=".png",): ## might be good to organize different plot types into subdirectories, but doesn't have to be an argument here
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
    Somewhat made redundant by the creation of get_dataframe, but I'll leave it for now
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
    Note: may want to include the current things that are expected in dataframe in this description

    Args:
    candDir: path to candidate directory 
    fitDir: path to fit directory 
    models: list of models to search for/consider
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
    ## may not need start and stop day, but commented out here in case it's useful later
    #startDay = [int(day.split('-')[0]) for day in dayList]
    #stopDay = [int(day.split('-')[1]) for day in dayList]
    for day, dayPath in zip(dayList, dayPathList):
        ## get lists for day level directories
        candPathList = glob.glob(os.path.join(dayPath, "*.csv")) ## could change to have a .dat argument option
        candList = [cand.split('/')[-1].split('.')[0].split('_')[1] for cand in candPathList] ## this is a bit of a mess, but it works (hopefully)
        for cand, candPath in zip(candList, candPathList): ## works around the issue of candidate_data being present in the candidate_fits directory, which is not the case for the countDailyFits function
            ## search for models at same time as candidate data
            for model in models:
                df.at[idx, 'day'] = day
                ## start and stop day might be unnecessary, could just do this at later point
                #df.at[idx, 'startDay'] = startDay[idx] 
                #df.at[idx, 'stopDay'] = stopDay[idx]
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
    
    df.to_csv(plotDir(name='statsDataframe',ext='.csv')) if save else None
    ## Not exactly the intended use of plotDir, but it works (probably)
    return df ## generally, most items returned in df will be strings, with a small number of bools and np.nan values




## Functions to plot daily candidate stats
## these functions could probably be combined for ease of calling, perhaps with argument to determine which plot(s) to make

def plotDailyCand(save=True): ## needs to be modified to accept dataframe instead
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
    plt.savefig(plotDir("numDailyCandHist")) if save else None
    plt.clf()


def plotCumDailyCand(save=True): ## needs to be modified to accept dataframe instead
    ## could switch to seaborn to make smoother/prettier curve
    '''
    Plot the cumulative number of candidates per day
    
    Args:
    save: boolean to determine whether to save the plot or not
    '''
    plt.plot(dayCount,cumDaily)
    plt.xlabel("Days Since Start")
    plt.ylabel('Cumulative Number of Candidates')
    plt.savefig(plotDir("cumDailyCand")) if save else None
    plt.clf()


def plotDailyCandRolling(save=True): ## needs to be modified to accept dataframe instead
    '''
    Plot the number of candidates per day with a rolling average
    
    Args:
    save: boolean to determine whether to save the plot or not
    '''
    plt.plot(dayCount, numDaily)
    plt.plot(dayCount, pd.Series(numDaily).rolling(7).mean())
    plt.xlabel("Days Since Start")
    plt.ylabel('Number of Daily Candidates')
    plt.savefig(plotDir("numDailyCandRolling")) if save else None
    plt.clf()




## Functions to plot fitting stats

## need a daily fits plot to be made in addition to the cumulative one


def plotFitCum(models=args.models, save=True): ## needs to be modified to accept dataframe instead
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
        plt.plot(dayCount,value, label=key, marker='o') ## need to make a colormap for better visualization
        plt.xlabel("Days Since Start")
        plt.ylabel('Count')
        ## need to cmap or something for controlling colors
    
    plt.title('Cumulative Number of Fits for All Models')
    plt.legend()
    plt.savefig(plotDir("cumDailyFits_all")) if save else None
    plt.clf()
    return modelDict ## maybe not necessary to return this
    

def plotUnfit(df, models= args.models, save=True): ## assumes use of dataframe
    '''
    Plot the number of candidates that were not fit for each day

    Args:
    df: dataframe containing the stats data (expected to be output of get_dataframe) (required)
    models: list of models to search for
    save: boolean to determine whether to save the figure or not
    '''

    ## compiling data for plotting

    ## find unique values in df['day'] and use those to create a list of days
    dayList = np.array(df['day'].unique().tolist())
    dayCount = np.arange(len(dayList)) ## might be better to switch to start day count or something

    ## find number of candidates that were not fit for each day, seperated by model
    ## df uses conditionals in list comprehension, which is wrapped in a dict comprehension
    ## slightly long expression, but should be efficient (dataframe filtering could be slow potentially)
    unfit = {model: 
    np.array([len(df[(df['model' == model]) & (df['day'] == day) & (df['fitBool'] == False)]) 
    for day in dayList]) 
    for model in models}
    unfit['Total'] = np.array([len(df[(df['day'] == day) & (df['fitBool'] == False)]) for day in dayList])

    ## find number of candidates that were fit for each day, seperated by model (for plotting stats later)
    fit = {model: 
    np.array([len(df[(df['model' == model]) & (df['day'] == day) & (df['fitBool'] == True)]) 
    for day in dayList]) 
    for model in models}
    fit['Total'] = np.array([len(df[(df['day'] == day) & (df['fitBool'] == True)]) for day in dayList])

    ## total number of fit and unfit per day (for plotting stats later)
    allfit = {key: unfit[key] + fit[key] for key in unfit.keys()}

    ## data plotting

    ## plot the number of candidates that were not fit for each day
    ## should add a fig, ax = plt.subplots() to allow for better customization
    for key, value in unfit.items(): ## one line conditional here is to exclude the total from the histogram
        plt.plot(dayCount, value, label=key, marker='o') if key != 'Total' else None
    plt.xlabel("Days Since Start")
    plt.ylabel('Count')
    plt.title('Number of Unfit Candidates') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("numDailyUnfit")) if save else None
    plt.clf()

    ## plot histogram of number of candidates that were not fit for each day by model
    for key, value in unfit.items():
        plt.hist(value, label=key)
    plt.xlabel("Number of Unfit Candidates per Day")
    plt.ylabel('Count')
    plt.title('Histogram of Number of Unfit Candidates per Day') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("numDailyUnfitModelHist")) if save else None
    plt.clf()

    ## plot histogram of number of candidates that were not fit for each day
    plt.hist(unfit['Total'], bins=20) ## could fine tune the number of bins
    plt.xlabel("Number of Unfit Candidates per Day")
    plt.ylabel('Count')
    plt.savefig(plotDir("numDailyUnfitTotalHist")) if save else None
    plt.clf()

    ## plot rolling average of number of candidates that were not fit for each day
    for key, value in unfit.items():
        plt.plot(dayCount, pd.Series(value).rolling(7).mean(), label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Count')
    plt.title('Number of Unfit Candidates') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("dailyUnfit")) if save else None
    plt.clf()

    ## plot cumulative number of candidates that were not fit for each day
    for key, value in unfit.items():
        plt.plot(dayCount, np.cumsum(value), label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Count')
    plt.title('Cumulative Number of Unfit Candidates') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("cumDailyUnfit")) if save else None
    plt.clf()

    ## plot fraction of candidates that were not fit for each day
    for key, value in allfit.items():
        plt.plot(dayCount, value, label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Ratio')
    plt.title('Fraction of Unfit Candidates to Total') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("fracDailyUnfit")) if save else None
    plt.clf()

    ## plot rolling average of fraction of candidates that were not fit for each day
    for key, value in allfit.items():
        plt.plot(dayCount, pd.Series(value).rolling(7).mean(), label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Ratio')
    plt.title('Fraction of Unfit Candidates to Total \n (One Week Rolling Average)') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("fracDailyUnfitRolling")) if save else None

    ## plot cumulative fraction of candidates that were not fit for each day 
    for key, value in allfit.items():
        plt.plot(dayCount, np.cumsum(value), label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Ratio')
    plt.title('Cumulative Fraction of Unfit Candidates to Total') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("cumFracDailyUnfit")) if save else None
    plt.clf()

    ## plot rolling average of cumulative fraction of candidates that were not fit for each day
    for key, value in allfit.items():
        plt.plot(dayCount, pd.Series(np.cumsum(value)).rolling(7).mean(), label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Ratio')
    plt.title('Cumulative Fraction of Unfit Candidates to Total \n (One Week Rolling Average)') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("cumFracDailyUnfitRolling")) if save else None
    plt.clf()

    ## maybe a simple bar chart of unfit candidates? (could be useful for a quick glance)
    ## could also add a stacked bar chart of fit and unfit candidates

    ## probably don't need to return anything here



## plot the fit time statistics
def plotSamplingTime(df, models=args.models, save=True):
    '''
    Plot the sampling time statistics for the given dataframe.

    Args:
    df: dataframe containing the stats data (expected to be output of get_dataframe) (required)
    models: list of models to search for
    save: boolean to determine whether to save the figure or not
    '''

    ## get the fit time data
    dayList = np.array(df['day'].unique().tolist())
    fitTime = {model: 
    np.array([float(df[(df['model' == model]) & (df['day'] == day) & (df['fitBool'] == True)]['sampling_time']) 
    for day in dayList]) 
    for model in models}
    fitTime['Total'] = np.array([float(df[(df['day'] == day) & (df['fitBool'] == True)]['sampling_time']) for day in dayList])

    ## data plotting

    ## plot histogram of fit time data
    for key, value in fitTime.items(): ## this has issue of the value being an array of arrays (e.g each day will have an array of fit times). Wasn't an issue in plotUnfit() because each day had a single value 
        ## I suppose I could just flatten it?
        plt.hist(value.flatten(), label=key)  if key != 'Total' else None 
        ## could fine tune the number of bins
    plt.xlabel("Sampling Times (s)")
    plt.ylabel('Count')
    plt.title('Sampling Times for Each Model') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("fitTimeHistModel")) if save else None
    plt.clf()

    ## summing over axis=1 means that each day will have a single value
    ## plot histogram of total daily fit time
    plt.hist(np.sum(fitTime['Total'],axis=1)) ## could fine tune the number of bins
    plt.xlabel("Sampling Times (s)")
    plt.ylabel('Count')
    plt.title('Daily Sampling Times')
    plt.savefig(plotDir("fitTimeHistTotal")) if save else None
    plt.clf()

    ## plot the daily average fit time for each model
    for key, value in fitTime.items(): 
        plt.plot(dayList, np.mean(value,axis=1), label=key) ## should be right axis?
    plt.xlabel("Days Since Start")
    plt.ylabel('Sampling Time (s)')
    plt.title('Average Daily Sampling Time') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("dailyFitTimeAvg")) if save else None
    ## could do a version with std error bars as well

    ## plot the daily median fit time for each model
    for key, value in fitTime.items():
        plt.plot(dayList, np.median(value,axis=1), label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Sampling Time (s)')
    plt.title('Median Daily Sampling Time') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("dailyFitTimeMedian")) if save else None
    plt.clf()

    ## plot the daily median fit time for each model (rolling average)
    for key, value in fitTime.items():
        plt.plot(dayList, pd.Series(np.median(value,axis=1)).rolling(7).mean(), label=key)
    plt.xlabel("Days Since Start")
    plt.ylabel('Sampling Time (s)')
    plt.title('Median Daily Sampling Time \n (One Week Rolling Average)') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("dailyFitTimeMedianRolling")) if save else None
    plt.clf()

    ## plot the cumulative daily fit time for each model
    for key, value in fitTime.items():
        plt.plot(dayList, np.cumsum(np.sum(value, axis=1)), label=key) 
    plt.xlabel("Days Since Start")
    plt.ylabel('Sampling Time (s)')
    plt.title('Cumulative Sampling Time') ## should these have titles?
    plt.legend()
    plt.savefig(plotDir("cumFitTime")) if save else None
    plt.clf()
    



## To Do:

## plot rolling average of each model fit time -- maybe unneeded?

## add a file size counter and plotter potentially (would use os.path.filesize())

## add a timeit option to functions to determine how long they take to run

## perhaps a function that finds the model with the highest log_likelihood for each candidate and then plots some stuff about which models were 'most likely' over time and compared to one another

## time to fit vs. log likelihood plot?