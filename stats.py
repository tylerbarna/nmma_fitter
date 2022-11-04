## Essentially intended to be a way to create some nice stats plots for the paper
## July 2021-July 2022: 1807 candidates, average of 4.36 candidates per day

## Need to stylize the plots; could define a function to outline a consistent plot style and size depending on plot type to reduce repetition - see https://stackoverflow.com/questions/51711438/matplotlib-how-to-edit-the-same-plot-with-different-functions and https://matplotlib.org/1.5.3/users/style_sheets.html for more info
## need to fig,ax stuff

## could probably consolidate some of the plotting functions into one function for each topic (e.g. one function for plotting the number of fits, one for plotting the number of unfit, etc.)

## alternatively, could change these into methods of a class that takes the dataframe as the object (e.g. df.plotDailyCand() ) 

import argparse
import glob
import json
import os
import sys
import time

import matplotlib as mpl
import matplotlib.dates as dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from astropy.time import Time

#from scipy.interpolate import make_interp_spline as spline

## set plot style
plt.style.use('seaborn-bright')
mpl.rcParams.update({"axes.grid" : True})

## argument for folder to run stats on
parser = argparse.ArgumentParser()
parser.add_argument("-c","--candDir", type=str, default=None, help="Path to the candidate directory")
parser.add_argument("-f","--fitDir", type=str, default=None, help="Path to the fits directory")
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-o', '--outdir', type=str, default=os.path.join('./outdir/stats/',time.strftime("%Y%m%d-%H%M%S"),''))
parser.add_argument("-m","--models", nargs="+", default = ["TrPi2018","nugent-hyper", "Piro2021","Bu2019lm"], choices = ["TrPi2018","nugent-hyper", "Piro2021","Bu2019lm"], help="which models to analyse with the fit stats")
parser.add_argument('-df','--datafile',type=str, default=None, help="path to the csv file that's generated by the stats.py script")
args = parser.parse_args()

## to change to correct directory
os.chdir(sys.path[0])
print("Current working directory: {0}\n".format(os.getcwd())) if args.verbose else None

## compilation of lists for use in plotting (pre-dataframe implementation)
## post dataframe implementation: these should eventually be removed and plots should be updated to use the dataframe
if args.candDir:
    dayList = glob.glob(os.path.join(args.candDir, "/*/"))
    
    dayCount = [day for day in range(0,len(dayList))]
    
    numDaily = [len(glob.glob(day + "/*.csv")) for day in dayList]
    
    candList = glob.glob(args.candDir + "*/*.csv")

    cumDaily = np.cumsum(numDaily)
else:
    print("No candidate directory specified, cannot run some stats\n")

if args.fitDir:
    fit_dayList = glob.glob(args.fitDir + "*")
    
    ## attempted dict comprehension for finding all instances of logs
    logDict = {model: glob.glob(os.path.join(args.fitDir,'*',model+'.log')) for model in args.models}
    jsonDict = {model: glob.glob(os.path.join(args.fitDir,'*',model+'_result.json')) for model in args.models}
    ## the way these are written, it may have issues for plotting if some days don't have all models
else:
    print("No candidate directory specified, cannot run some stats\n")


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


## function is currently unused/incomplete, wanted to at least start it and make a commit with it
def plotstyle(type=None, **kwargs): ## should add an option to pass kwargs to the plot function
    '''
    Sets the style of the plots to be consistent across the paper using matplotlib's style sheets
    
    Args:
    type: type of plot to be generated (e.g. 'histogram', 'scatter')
    **kwargs: anything you would pass to matplotlib
    '''
    fig, ax = plt.subplots(**kwargs) ## not super sure on this implementation
    
    plt.style.use('seaborn-whitegrid')
    #plt.rcParams['font.family'] = 'serif'
    #plt.rcParams['font.serif'] = 'Times New Roman'
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['axes.labelweight'] = 'bold'
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    plt.rcParams['legend.fontsize'] = 12
    plt.rcParams['figure.titlesize'] = 12

    return(fig,ax)


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
        print('provide a file to search!\n')
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
        try: 
            with open(file,'r') as f:
                data = json.load(f)
                jsonDict = {param: data[param] for param in jsonList}
                
        except: ## in event that json file isn't read correctly
            print('error reading json file: {} \n'.format(file))
            jsonDict = {param: np.nan for param in jsonList}
        finally:
            f.close()
            print('jsonDict: {}\n'.format(jsonDict)) if args.verbose else None
            return jsonDict
    elif not file: ## for use case where no json is found when the pandas dataframe is created
        jsonDict = {param: np.nan for param in jsonList} ## np.nan is used to make it easier to plot later without having to deal with NoneType
        print('no json file found/provided')
        print('jsonDict: {}\n'.format(jsonDict)) if args.verbose else None
        return jsonDict
    else: ## case where file argument is not provided
        print('provide a file to search!\n')
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
        print('provide a day to count fits for!\n')
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
    startTime = time.time() ## for timing purposes

    if file:
        print('loading dataframe from file: {}'.format(file)) if args.verbose else None
        df = pd.read_csv(file,index_col=0).fillna(value=np.nan) ## needs to be tested to ensure compatibility with saved dataframe
        df['startDate'] = pd.to_datetime(df['startDate'])
        df['stopDate'] = pd.to_datetime(df['stopDate'])
        return df ## don't need an else since the function will exit if file is provided
    
    ## need to explicitly add all columns here maybe? Will mess with any additional parameters provided to get_json if that is added to this function in the future
    col = ['day','startDate','stopDate','dayPath','cand','candPath','model', 'fitPath','json','fitBool','sampling_time', 'sampler', 'log_evidence', 'log_evidence_err', 'log_noise_evidence', 'log_bayes_factor'] ## addition of start and stop day needs to be tested
    df = pd.DataFrame(columns=col) ## create empty dataframe with columns
    ## set the type for the columns that will be added to the dataframe
    df['day'] = df['day'].astype('str')
    df['startDate'] = df['startDate'].astype(np.datetime64) ## could use this as a way to set bounds on the data that's collected ahead of time
    df['stopDate'] = df['stopDate'].astype(np.datetime64) ## going to use convention that stopDate is the day to be plotted, as that corresponds to the day of the last observation
    df['dayPath'] = df['dayPath'].astype('str')
    df['cand'] = df['cand'].astype('str')
    df['candPath'] = df['candPath'].astype('str')
    df['model'] = df['model'].astype('str')
    df['fitPath'] = df['fitPath'].astype('str')
    df['json'] = df['json'].astype('str')
    df['fitBool'] = df['fitBool'].astype('bool')

    ## should probably change these to be an additional argument passed to get_json, specifically the params argument
    ## are there other useful parameters in the json file that should be included?

    df['sampling_time'] = df['sampling_time'].astype('float')
    df['sampler'] = df['sampler'].astype('str')
    df['log_evidence'] = df['log_evidence'].astype('float')
    df['log_evidence_err'] = df['log_evidence_err'].astype('float')
    df['log_noise_evidence'] = df['log_noise_evidence'].astype('float')
    df['log_bayes_factor'] = df['log_bayes_factor'].astype('float')
    
    dayPathList = glob.glob(os.path.join(candDir, "*",'')) ## list of paths to the days that have candidates
    print('dayPathList: {}\n'.format(dayPathList)) if args.verbose else None
    dayList = [dayPath.split('/')[-2] for dayPath in dayPathList]

    idx = 0 ## used to keep track of the index of the dataframe when defining new values

    for day, dayPath in zip(dayList, dayPathList):
        ## get lists for day level directories
        candPathList = glob.glob(os.path.join(dayPath, "*.csv")) ## could change to have a .dat argument option
        candList = [cand.split('/')[-1].split('.')[0].split('_')[1] for cand in candPathList] ## this is a bit of a mess, but it works (hopefully)
        for cand, candPath in zip(candList, candPathList): ## works around the issue of candidate_data being present in the candidate_fits directory, which is not the case for the countDailyFits function
            ## search for models at same time as candidate data
            for model in models:
                df.at[idx, 'day'] = day
                startDate, stopDate = df.at[idx, 'day'].split('-', 1) ## create values for start and stop day columns
                startDate, stopDate = Time(startDate, format='jd').datetime64, Time(stopDate, format='jd').datetime64 
                ## might be inefficient, adding the date columns makes sample take 1.02 seconds, without it takes 0.88 seconds (15% increase)
                ## actually, running a second time, it only takes 0.81 seconds with the date columns, so it might not matter
                df.at[idx, 'startDate'] = startDate
                df.at[idx, 'stopDate'] = stopDate
                df.at[idx, 'dayPath'] = dayPath
                df.at[idx, 'cand'] = cand
                df.at[idx, 'candPath'] = candPath
                df.at[idx, 'model'] = model

                ## check if fit was completed
                fitPath = os.path.join(fitDir, day, cand,"")
                print('fitPath: {}'.format(fitPath)) if args.verbose else None
                df.at[idx, 'fitPath'] = fitPath
                ## now find json
                jsonPath = os.path.join(fitPath, model+'_result.json')
                jsonBool = True if os.path.exists(jsonPath) else False
                
                print('jsonPath: {}'.format(jsonPath)) if args.verbose else None
                if jsonBool:
                    df.at[idx, 'json'] = jsonPath
                    df.at[idx, 'fitBool'] = True
                    ## now get values from json
                    jsonDict = get_json(file=jsonPath)
                    for key, value in jsonDict.items():
                        df.at[idx, key] = value
                elif not jsonBool:
                    df.at[idx, 'json'] = np.nan
                    df.at[idx, 'fitBool'] = False
                    ## now get values from json
                    jsonDict = get_json(file=False)
                    for key, value in jsonDict.items():
                        df.at[idx, key] = np.nan ## should be np.nan
                idx += 1
                print('get_dataframe idx: {}'.format(idx)) if args.verbose else None
    
    df.sort_values(by=['day','cand','model'], inplace=True)
    df.to_csv(plotDir(name='statsDataframe',ext='.csv')) if save else None
    ## Not exactly the intended use of plotDir, but it works (probably)
    print('completed dataframe creation') if args.verbose else None
    
    print('time to create dataframe: {} seconds\n'.format(time.time()-startTime)) if args.verbose else None

    return df ## generally, most items returned in df will be strings, with a small number of bools and np.nan values



## Functions to plot daily candidate stats
## these functions could probably be combined for ease of calling, perhaps with argument to determine which plot(s) to make
def plotCands(df, save=True): 
    '''
    plot the number of candidates per day as both a line plot (numDailyCand) and histogram (numDailyCandHist), plot rolling average of number of candidates (numDailyCandRolling),
    plot cumulative number of candidates over time (cumDailyCand)
    
    Args:
    df: dataframe with candidate data from get_dataframe function
    save: boolean to determine whether to save the plot or not
    '''

    ## get count of days and unique dates for plotting
    dayList = df['day'].unique()
    dateIdx = df['day'].drop_duplicates().index
    dateList = df['stopDate'][dateIdx] ## this is the date of the last observations made for the fitting
    print('dayList: {}'.format(dayList)) if args.verbose else None
    print('dateList: {}'.format(dateList)) if args.verbose else None

    ## get number of candidates per day
    numDaily = np.array([len(df[df['day'] == day]['candPath'].unique()) for day in dayList])
    print('numDaily: {}\n'.format(numDaily)) if args.verbose else None
    
    numDailyRolling = pd.Series(numDaily).rolling(7).mean()
    print('numDailyRolling: {}'.format(numDailyRolling)) if args.verbose else None
    
    cumDaily = np.cumsum(numDaily)
    print('cumDaily: {}\n'.format(cumDaily)) if args.verbose else None
    
    ## plot number of candidates per day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white') 
    ax.plot(dateList, numDaily,
            color='black',linewidth=2)
    plt.xticks(rotation=15)
    ax.set_xlabel("Date") 
    ax.set_ylabel('Candidates Per Day')
    plt.savefig(plotDir("numDailyCand")) if save else None
    print('completed numDailyCand plot') if args.verbose else None
    plt.clf()
     
    ## plot histogram of number of candidates per day
    fig, ax = plotstyle(figsize=(10,6), facecolor='white')
    sns.histplot(numDaily, kde=True, 
                 bins=numDaily.max(), ax=ax) ## I think having bins equal to the max number of candidates per day looks best
    ax.set_xlabel("Candidates Per Day")
    ax.set_ylabel('Count')
    plt.savefig(plotDir("numDailyCandHist")) if save else None
    print('completed numDailyCandHist plot') if args.verbose else None
    plt.clf()
    
    #plot 7 day rolling average of candidates per day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    ax.plot(dateList, numDailyRolling,
            color='black',linewidth=2) ## note: this won't work with one week of data
    plt.xticks(rotation=15)
    ax.set_xlabel("Date")
    ax.set_ylabel('Candidates Per Day\n(Rolling Average)') ## needs title
    plt.savefig(plotDir("numDailyCandRolling")) if save else None
    print('completed numDailyCandRolling plot') if args.verbose else None
    plt.clf()
    
    ## plot cumulative number of candidates per day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    ax.plot(dateList,cumDaily,
            color='black',linewidth=2)
    plt.xticks(rotation=15)
    ax.set_xlabel("Date")
    ax.set_ylabel('Candidate Count')
    plt.savefig(plotDir("cumDailyCand")) if save else None
    print('completed cumDailyCand plot\n') if args.verbose else None
    plt.clf()
    
    

## Functions to plot fitting stats
## need a daily fits plot to be made in addition to the cumulative one
def plotFits(df,models=args.models, save=True): 
    '''
    plot the cumulative number of fits for each model
    
    Args:
    df: dataframe with candidate data from get_dataframe function
    models: list of models to search for
    save: boolean to determine whether to save the figure or not
    '''
    ## modelDict creates dict of cumulative fit counts for each model so they can be plotted together
    modelDict = {}
    ## get count of days and unique dates for plotting
    dayList = df['day'].unique()
    dateIdx = df['day'].drop_duplicates().index
    dateList = df['stopDate'][dateIdx] ## this is the date of the last observations made for the fitting
    print('dayList: {}'.format(dayList)) if args.verbose else None
    print('dateList: {}\n'.format(dateList)) if args.verbose else None
    ## number of daily candidates
    numDaily = np.array([len(df[df['day'] == day]['candPath'].unique()) for day in dayList])
    cumDaily = np.cumsum(numDaily)
    
    for model in models: ## get cumulative number of fits for each model, plot, save, and add to modelDict
        ## compile cumulative number of fits for each model
        modelCount = np.array([len(df[(df['model']==model) & (df['day'] == day) & (df['fitBool'] == True)]) for day in dayList])
        modelCum = np.array(modelCount.cumsum())
        #print('modelCum: {}'.format(modelCum) if args.verbose else None
        modelDict[model] = modelCum
        print('modelCum: {}'.format(modelCum)) if args.verbose else None
        
        ## plot cumulative number of fits for each model
        ## perhaps this could be a grid of subplots
        fig, ax = plotstyle(figsize=(8,6), facecolor='white')
        ax.plot(dateList,modelCum, label=model)
        ax.plot(dateList, cumDaily, label='Candidate Count', color='black', linewidth=2)
        ax.set_xlabel("Date")
        plt.xticks(rotation=15)
        ax.set_ylabel('Count')
        ax.set_title('{}'.format(model))
        ax.legend()
        plt.savefig(plotDir("cumDailyFits_"+model)) if save else None
        print('completed cumDailyFits plot for {} \n'.format(model)) if args.verbose else None
        plt.clf()
    try: ## using a try here because this could totally break if the modelDict has different lengths for each model
        modelDict['Total'] = sum(map(np.array,modelDict.values())).tolist()
    except:
        print('Keys in modelDict probably do not have the same length')
        pass
    ## now plot all models together
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    for key, value in modelDict.items(): 
        ax.plot(dateList,value, label=key, alpha=0.7) if key != 'Total' else None## need to make a colormap for better visualization
    ax.plot(dateList, cumDaily, label='Candidate Count', color='black', linewidth=2)
    plt.xticks(rotation=15)
    ax.set_xlabel("Date")
    ax.set_ylabel('Count')
    ## need to cmap or something for controlling colors
    #ax.set_title('Cumulative Number of Fits')
    ax.legend()
    plt.savefig(plotDir("cumDailyFitsAll")) if save else None ## need to make a version that adds a residual plot below to compare models
    ax.set_yscale('log')
    plt.savefig(plotDir("cumDailyFitsAllLog")) if save else None
    print('completed cumDailyFits plot for all models \n') if args.verbose else None
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
    ## get count of days and unique dates for plotting
    dayList = df['day'].unique()
    dateIdx = df['day'].drop_duplicates().index
    dateList = df['stopDate'][dateIdx] ## this is the date of the last observations made for the fitting
    print('dayList: {}'.format(dayList)) if args.verbose else None
    print('dateList: {}\n'.format(dateList)) if args.verbose else None

    ## find number of candidates that were not fit for each day, seperated by model
    ## df uses conditionals in list comprehension, which is wrapped in a dict comprehension
    ## slightly long expression, but should be efficient (dataframe filtering could be slow potentially)
    unfit = {model: 
    np.array([len(df[(df['fitBool'] == False) & (df['model'] == model) & (df['day'] == day)])
    for day in dayList])
    for model in models}
    unfit['Total'] = np.array([len(df[ (df['fitBool'] == False) & (df['day'] == day)]) for day in dayList])

    ## find number of candidates that were fit for each day, seperated by model (for plotting stats later)
    fit = {model: 
    np.array([len(df[(df['fitBool'] == True) & (df['model'] == model) & (df['day'] == day)])
    for day in dayList])
    for model in models}
    fit['Total'] = np.array([len(df[(df['fitBool'] == True) & (df['day'] == day)]) for day in dayList])

    ## total number of fit and unfit per day (for plotting stats later)
    allfit = {model: 
    np.array([len(df[ (df['model'] == model) & (df['day'] == day)])
    for day in dayList])
    for model in models}
    allfit['Total'] = np.array([len(df[ (df['day'] == day)]) for day in dayList])
    

    ## data plotting
    ## plot the number of candidates that were not fit for each day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    for key, value in unfit.items(): ## one line conditional here is to exclude the total from the histogram
        ax.plot(dateList, value, label=key, alpha=0.6) if key != 'Total' else None
    ax.set_xlabel("Date")
    ax.set_ylabel('Unfit Models')
    #ax.set_title('Number of Unfit Candidates') ## should these have titles?
    plt.xticks(rotation=15)
    ax.legend()
    plt.savefig(plotDir("numDailyUnfit")) if save else None
    plt.clf()

    ## should fix styling as it's currently unclear
    ## plot histogram of number of candidates that were not fit for each day by model
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    for key, value in unfit.items():
        sns.histplot(value, label=key,alpha=0.75, ax=ax) if key != 'Total' else None 
    ax.set_xlabel("Daily Unfit Count")
    ax.set_ylabel('Count')
    #ax.set_title('Number of Unfit Candidates per Day') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("numDailyUnfitModelHist")) if save else None
    plt.clf()

    ## plot histogram of number of candidates that were not fit for each day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    sns.histplot(unfit['Total'], bins=20, ax=ax) ## could fine tune the number of bins
    ax.set_xlabel("Number Unfit")
    ax.set_ylabel('Count')
    #ax.set_title("Number of Unfit Candidates per Day")
    plt.savefig(plotDir("numDailyUnfitTotalHist")) if save else None
    plt.clf()

    ## plot rolling average of number of candidates that were not fit for each day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    for key, value in unfit.items():
        ax.plot(dateList, pd.Series(value).rolling(7).mean(), label=key)
    ax.set_xlabel("Date")
    ax.set_ylabel('Unfit models\n (7 day rolling average)')
    #ax.set_title('Number of Unfit Candidates') ## should these have titles?
    plt.xticks(rotation=15)
    ax.legend()
    plt.savefig(plotDir("numDailyUnfitRolling")) if save else None
    plt.clf()

    ## plot cumulative number of candidates that were not fit for each day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    for key, value in unfit.items():
        ax.plot(dateList, np.cumsum(value), label=key)
    ax.set_xlabel("Date")
    ax.set_ylabel('Cumulative Unfit')
    #ax.set_title('Cumulative Number of Unfit Candidates') ## should these have titles?
    plt.xticks(rotation=15)
    ax.legend()
    plt.savefig(plotDir("cumDailyUnfit")) if save else None
    plt.clf()
   
    ## plot fraction of candidates that were not fit for each day
    fig, ax = plotstyle(figsize=(8,6), facecolor='white')
    for key, value in unfit.items():
        fracValue = value/allfit['Total']
        ax.plot(dateList, fracValue, label=key) if key != 'Total' else None
    ax.set_xlabel("Date")
    ax.set_ylabel('Unfit Ratio')
    #ax.set_title('Fraction of Unfit Candidates to Total') ## should these have titles?
    plt.xticks(rotation=15)
    ax.legend()
    plt.savefig(plotDir("fracDailyUnfit")) if save else None
    plt.clf()

    ## plot rolling average of fraction of candidates that were not fit for each day
    fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
    for key, value in unfit.items(): ## is this the correct method for rolling average ratio?
        fracValue =  pd.Series(value).rolling(7).mean()/pd.Series(allfit['Total']).rolling(7).mean()
        ax.plot(dateList, fracValue, label=key) if key != 'Total' else None
    ax.set_xlabel("Date")
    ax.set_ylabel('Unfit Ratio')
    #ax.set_title('Fraction of Unfit Candidates to Total \n (One Week Rolling Average)') ## should these have titles?
    plt.xticks(rotation=15)
    ax.legend()
    plt.savefig(plotDir("fracDailyUnfitRolling")) if save else None

    '''
    ## this seems to be busted in some way 
    ## (actually, it might not be the most useful plot)
    ## plot cumulative fraction of candidates that were not fit for each day 
    fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
    for key, value in allfit.items():
        fracValue = np.cumsum(value)/np.cumsum(allfit['Total'])
        ax.plot(dayCount, np.cumsum(fracValue), label=key) if key != 'Total' else None
    ax.set_xlabel("Days Since Start")
    ax.set_ylabel('Unfit Ratio\n (Cumulative)')
    #ax.set_title('Cumulative Fraction of Unfit Candidates to Total') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("cumFracDailyUnfit")) if save else None
    plt.clf()
    
    ## plot rolling average of cumulative fraction of candidates that were not fit for each day
    fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
    for key, value in allfit.items():
        fracValue = pd.Series(np.cumsum(value)).rolling(7).mean()/pd.Series(np.cumsum(allfit['Total'])).rolling(7).mean()
        ax.plot(dayCount, fracValue, label=key) if key != 'Total' else None
    ax.set_xlabel("Days Since Start")
    ax.set_ylabel('Ratio')
    #ax.set_title('Cumulative Fraction of Unfit Candidates to Total \n (One Week Rolling Average)') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("cumFracDailyUnfitRolling")) if save else None
    plt.clf()
    '''
    
    
    ## maybe a simple bar chart of unfit candidates? (could be useful for a quick glance)
    ## could also add a stacked bar chart of fit and unfit candidates

    ## probably don't need to return anything here



## plot the fit time statistics
def plotSamplingTimes(df, models=args.models, save=True):
    '''
    Plot the sampling time statistics for the given dataframe.

    Args:
    df: dataframe containing the stats data (expected to be output of get_dataframe) (required)
    models: list of models to search for
    save: boolean to determine whether to save the figure or not
    '''

    ## get the fit time data
    dayList = df['day'].unique() ## oh, may need to switch to dayCount when plotting later
    dayCount = np.arange(len(dayList)) ## might be better to switch to start day count or something

    ## create a dictionary of fit times for each model
    fitTime = {}
    for model in models: ## won't iterate over Total (which is good)
        fitTime[model] = np.array([
            df[(df['fitBool'] == True) & (df['day'] == day) & (df['model'] == model)]['sampling_time'].to_numpy(copy=True).ravel() for day in dayList
        ], dtype=object)
        try:
            fitTime[model] = fitTime[model].reshape(len(dayList),) ## flatten the array
        except:
            fitTime[model] = np.tile(np.array([np.nan],dtype='float64'),(len(dayList),))
            fitTime[model] = fitTime[model].reshape(len(dayList),) ## flatten the array
        print('model {0} fit times: {1}\n'.format((model, fitTime[model]))) if args.verbose else None
        print('model {0} fit times shape: {1}\n'.format((model, fitTime[model].shape))) if args.verbose else None
    
    fitTime['Total'] = np.array([np.concatenate([value[idx].flatten() for key, value in fitTime.items() if key != 'Total']) for idx in range(len(dayList))])
    print ('total fit time: {}\n'.format(fitTime['Total'])) if args.verbose else None
    print ('total fit time shape: {}\n'.format(fitTime['Total'].shape)) if args.verbose else None
    fitTime['Total'] = fitTime['Total'].reshape(len(dayList),) 
    
    '''
    ## debugging to check if the fit times are being stored correctly
    t1 = [0]*len(dayList)
    t2 = [0]*len(dayList)
    for idx in range(len(dayList)):
        t1[idx] = 0
        for key, value in fitTime.items():
            if key == 'Total':
                continue
            t1[idx] += np.nansum(value[idx]) 
            
        t2[idx] = np.nansum(fitTime['Total'][idx])
    if np.array_equal(t1,t2):
        print('t1 and t2 are equal') if args.verbose else None
        
    else:
        print('t1 and t2 are not equal') if args.verbose else None
    print('t1: {}'.format(t1)) if args.verbose else None
    print('') if args.verbose else None
    print('t2: {}'.format(t2)) if args.verbose else None
    print('') if args.verbose else None
    print('t1-t2: {}'.format(np.array(t1)-np.array(t2))) if args.verbose else None
    print('') if args.verbose else None
    print('t1 shape: {}'.format(np.array(t1).shape)) if args.verbose else None
    print('t2 shape: {}'.format(np.array(t2).shape)) if args.verbose else None
    print('t1 sum: {}'.format(np.nansum(t1))) if args.verbose else None
    print('t2 sum: {}'.format(np.nansum(t2))) if args.verbose else None
    print('t1 - tw sum: {}'.format(np.nansum(np.array(t1)-np.array(t2)))) if args.verbose else None
    print ('total fit time: {}'.format(fitTime['Total'])) if args.verbose else None
    print ('total fit time shape: {}'.format(fitTime['Total'].shape)) if args.verbose else None
    print() if args.verbose else None
    '''

    ## data plotting
    fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
    for key, value in fitTime.items(): ## this has issue of the value being an array of arrays (e.g each day will have an array of fit times). Wasn't an issue in plotUnfit() because each day had a single value 
        ## should pull this out maybe so it doesn't look as comnplicated
        fitTimeValue = np.concatenate(fitTime[key],axis=None).ravel() 
        sns.histplot(fitTimeValue, label=key,ax=ax, alpha=0.5, kde=True)  if key != 'Total' else None ## could fine tune the number of bins
    ax.set_xlabel("Sampling Times (s)")
    ax.set_ylabel('Count')
    #ax.set_title('Sampling Times for Each Model') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("fitTimeHistModel")) if save else None
    plt.clf()

    ## plot histogram of total daily fit time
    totalDailyFitTime = np.concatenate(fitTime['Total'],axis=None).ravel()
    fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
    sns.histplot(totalDailyFitTime,ax=ax) ## could fine tune the number of bins
    ax.set_xlabel("Sampling Times (s)")
    ax.set_ylabel('Count')
    #ax.set_title('Daily Sampling Times')
    plt.savefig(plotDir("fitTimeHistTotal")) if save else None
    plt.clf()

    ## plot the daily average fit time for each model
    fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
    for key, value in fitTime.items(): 
        meanFitTime = [np.mean(fitDay) for fitDay in fitTime[key]]
        ax.plot(dayCount, meanFitTime, label=key) ## should be right axis?
    ax.set_xlabel("Days Since Start")
    ax.set_ylabel('Sampling Time (s)')
    #ax.set_title('Average Daily Sampling Time') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("dailyFitTimeAvg")) if save else None
    ## could do a version with std error bars as well

    ## plot the daily median fit time for each model
    fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
    for key, value in fitTime.items():
        medianFitTime = [np.median(fitDay) for fitDay in fitTime[key]]
        plt.plot(dayCount, medianFitTime, label=key)
    ax.set_xlabel("Days Since Start")
    ax.set_ylabel('Sampling Time (s)')
    #ax.set_title('Median Daily Sampling Time') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("dailyFitTimeMedian")) if save else None
    plt.clf()

    ## plot the daily median fit time for each model (rolling average)
    for key, value in fitTime.items():
        medianFitTime = pd.Series([np.median(fitDay) for fitDay in fitTime[key]])
        plt.plot(dayCount, medianFitTime.rolling(7).mean(), label=key)
    ax.set_xlabel("Days Since Start")
    ax.set_ylabel('Sampling Time (s)')
    #ax.set_title('Median Daily Sampling Time \n (One Week Rolling Average)') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("dailyFitTimeMedianRolling")) if save else None
    plt.clf()

    ## plot the cumulative daily fit time for each model
    for key, value in fitTime.items():
        cumFitTime = np.cumsum([np.sum(fitDay) for fitDay in fitTime[key]])
        plt.plot(dayCount, cumFitTime, label=key) 
    ax.set_xlabel("Days Since Start")
    ax.set_ylabel('Sampling Time (s)')
    #ax.set_title('Cumulative Sampling Time') ## should these have titles?
    ax.legend()
    plt.savefig(plotDir("cumFitTime")) if save else None
    plt.clf()
    



## To Do:

## plot rolling average of each model fit time -- maybe unneeded?

## add a file size counter and plotter potentially (would use os.path.filesize())

## add a timeit option to functions to determine how long they take to run

## perhaps a function that finds the model with the highest log_likelihood for each candidate and then plots some stuff about which models were 'most likely' over time and compared to one another

## time to fit vs. log likelihood plot?

## testing stats functions

df = get_dataframe(candDir=args.candDir, models=args.models, save=False, file=args.datafile)   


# plotCands(df=df,save=True)
# print('completed daily candidate plots (1)\n') if args.verbose else None

plotFits(df=df)
print('completed cumulative fit plot (2)\n') if args.verbose else None

# plotUnfit(df=df)
# print('completed unfit candidate plot (3)\n') if args.verbose else None

# plotSamplingTimes(df=df)
# print('completed sampling time plot (4)\n') if args.verbose else None