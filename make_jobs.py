import subprocess
import os
import sys
import glob
import time
import argparse

import numpy as np

from datetime import date
from fit_utils import parse_csv

## print current date for log
#today = date.today()
#print("Current Date: "+str(today.strftime("%m-%d-%Y"))

## Allows for manual runs of specific dates
parser = argparse.ArgumentParser()
parser.add_argument("-d","--dataDir", type=str, default=None)

## Currently not in use: allows for manual fitting of a specific candidate or candidates (requires --dataDir to also be passed)
parser.add_argument("-c","--candidate", nargs="+", type=str, default=None)

## Should default to false (eg Slack bot does not post), but is called when one wants slack bot to post
parser.add_argument("-s","--slackBot", action='store_true')

## Currently not in use: models argument that takes multiple models in form of '--models "x" "y" "z"' for fitting and posting
## Would have to pass args.models as model_list when submitting jobs
## Would have to pass when executing fit bot as " ".join(f'"{m}"' for m in args.models)
parser.add_argument("-m","--models", nargs="+", type=str, default = ["Bu2019lm", "nugent-hyper", "TrPi2018", "Piro2021"])

## how long (in seconds) to wait on jobs until proceeding to pushing to schoty and posting to slack (default: 6 hours)
parser.add_argument("-t","--timeout",type=int,default=21600)

args = parser.parse_args()

## Attempt to pull latest data from schoty 
## This is a temporary test, still in process of troubleshooting the rsync issue with MSI 
## Current implementation (Late July 2021) works roughly half the time
try:
    subprocess.run("rsync -aOv --no-perms ztfrest@schoty.caltech.edu:/scr2/ztfrest/ZTF/ztfrest/candidates /home/cough052/shared/ztfrest")
except:
    print("failed to pull from schoty with rsync")
    try: ## Currently spaghetti, can be cleaned up once rsync is more consistent
        subprocess.run("scp -r ztfrest@schoty.caltech.edu:/scr2/ztfrest/ZTF/ztfrest/candidates /home/cough052/shared/ztfrest")
    except:
        print("failed to pull from schoty with scp")
        pass
    pass
time.sleep(30)
# Search directory and create a fit job for each

candidate_directory = "/panfs/roc/groups/7/cough052/shared/ztfrest/candidates/partnership"
if args.dataDir:
    latest_directory = args.dataDir
    print("Using manual folder %s" % latest_directory)
elif not args.dataDir:
    #latest_directory = max([f for f in os.listdir(candidate_directory)], key=lambda x: os.stat(os.path.join(candidate_directory,x)).st_mtime)
    latest_directory = np.sort(np.array([f.name for f in os.scandir(candidate_directory) if f.is_dir()]))[-1] ##this should probably work
    print("Using most recent directory %s" % latest_directory)
search_directory = os.path.join(candidate_directory,latest_directory,"") 

og_directory = os.getcwd()

# -TODO- List of jobs? Dictionary of jobs so they can be different for different models?
## Should probably rework so we remove dependence on location of job
job_name = {"Bu2019lm": "/panfs/roc/groups/7/cough052/barna314/nmma_fitter/KNjob.txt",
            "TrPi2018": "/panfs/roc/groups/7/cough052/barna314/nmma_fitter/GRBjob.txt",
            "nugent-hyper": "/panfs/roc/groups/7/cough052/barna314/nmma_fitter/SNjob.txt",
            "Piro2021": "/panfs/roc/groups/7/cough052/barna314/nmma_fitter/SCjob.txt",}

# List of models to run.
## Would like to change this so it's passed as an argument
model_list = args.models #["Bu2019lm", "TrPi2018", "nugent-hyper"]

# Outdirectory

os.chdir("/panfs/roc/groups/7/cough052/shared/ztfrest/candidate_fits")
outdir = os.path.join("./",latest_directory,"")

if os.path.isdir(outdir): ## if directory already exists, script will exit
    ## would like to change behavior so it checks that the plots exist for all candidates
    print("%s already exists in candidate_fits!" % latest_directory)
    quit()
elif not os.path.isdir(outdir):
    print("Candidate Directory: "+str(search_directory))
    os.makedirs(outdir)
    os.chmod(outdir, 0o774)
    os.makedirs(os.path.join(outdir,"candidate_data",""))
    os.chmod(os.path.join(outdir,"candidate_data",""), 0o774)
os.chdir(outdir) ##trying this to solve relative path issue
print("cwd: %s" % os.getcwd())


# -TODO- Can be replaced with something of the form 'filename.log'
log_filename = "fit.log"
log_filename = os.path.join("./",log_filename)


#could allow code to send batches to different machines

# find all the candidate in path
# Build these into a 2D array?
file_list = []
candidate_files = []
candidate_names = []

for file in glob.glob(search_directory + "/*.csv"):
    # file is the last item separated by slashes
    candfile = file.split('/')[-1]

    # candidate name is the second part of the filename separated by '_'
    candname = candfile.split('_')[1]
    
    file_list.append(file)
    candidate_files.append(candfile)
    candidate_names.append(candname)
    
    ## Explicitly list candidates in logfile
    logfile = open(log_filename, "a+")
    logfile.write("Found object: %s" % candname +"\n")
    logfile.close()

if not candidate_names: ## If there are no candidates found, quit here
    logfile = open(log_filename, "a+")
    logfile.write("No objects found \n")
    logfile.close()
    quit()
## want to alter structure so recurring job checks that all candidates have existing subdirectories
## rather than checking if a daily directory has been made; it would also be useful to have the option
## to set it so a specific candidate from a specific day could be fit 

# submit jobs to fit each candidate
job_id_list = []
live_jobs = {}

for ii in range(len(file_list)):
    # Load the file and certify that there are at least two detections
    data = parse_csv(file_list[ii], candidate_names[ii])
    detections = 0
    for line in data:
        # Check is not a non-detection
        if not np.isinf(float(line[3])):
            detections += 1
    if detections < 2:
        logfile = open(log_filename, "a+")
        logfile.write("Not enough data for candidate %s... continuing\n"%candidate_names[ii])
        logfile.close()
        continue
    #Submit jobs for each model
    for model in model_list:
        # -TODO- May want to eliminate shell=True. Apparently there are security holes associated with that.
        # Submit job
        ## Trying to add argument so it corrects directory change in nmma_fit
        ## Would like to also have it dynamically update job name to also include fit name
        command = subprocess.run("sbatch -J " + candidate_names[ii] +"_" + model + " " + job_name[model] + " " + file_list[ii] + " " + candidate_names[ii] + " " + model + " " + latest_directory, shell=True, capture_output=True)
        output = command.stdout
        outerr = command.stderr
        
        # conver output to an actual string
        output = str(output, 'utf-8')
        outerr = str(outerr, 'utf-8')

        logfile = open(log_filename, "a")
        logfile.write(outerr)
        logfile.close()
                
        # Job id is generally the last part of the job submission output
        job_id = int(output.split(' ')[-1])
        logfile = open(log_filename, "a")
        logfile.write("Submitted job for candidate " + candidate_names[ii] + ", model " + model + ". Job id: " + str(job_id) + "\n")
        logfile.close()
        
        job_id_list.append(job_id)
        live_jobs[job_id] = (candidate_names[ii], model)

# Check on jobs every minute to see if they finished.
# -TODO- Can change the wait time to be reasonable for release
startTime = time.time()
while len(live_jobs) > 0:
    time.sleep(60)
    currentTime = time.time()
    if currentTime-startTime > args.timeout:
        break

    finished_jobs = []
    ## not a huge concern for a finite number of jobs, but doesn't the current behavior rebuild finished_jobs with every loop?
    for id, (candname, model) in live_jobs.items():
        # nmma_fit makes a .fin file when done
        if os.path.isfile(candname + "_" + model + ".fin"):
            # Do something now that we know the job is done
            ## Need to alter behavior so it can handle a job failing before the .fin is made
            ## temporarily, this is addressed by there being a timeout for how long to wait before pushing to schoty
            logfile = open(log_filename, "a")
            logfile.write("Job " + str(id) + " for candidate " + candname + " with model " + model + " completed. Produced the following output: \n")
            
            outfile = open(str(id) + ".out", 'r')
            logfile.write(outfile.read())
            outfile.close()
                
            logfile.close()
            
            finished_jobs.append(id)
            # Check if there were errors?
            # -TODO- Push the data back.
        elif os.path.isfile(str(id) + ".err") and os.path.getsize(str(id) + ".err") != 0:
            logfile = open(log_filename, "a")
            logfile.write("Job " + str(id) + " for candidate " + candname + " encountered the following errors: \n")
            errorfile = open(str(id) + ".err", 'r')
            logfile.write(errorfile.read())
            errorfile.close()
            logfile.close()
            finished_jobs.append(id)

    # update the live job list
    for id in finished_jobs:
        del live_jobs[id]

# cleanup: delete finish files and empty error files
for model in model_list:
    for ii in range(len(file_list)):
        if os.path.isfile(candidate_names[ii] + "_" + model + '.fin'):
            os.remove(candidate_names[ii] + "_" + model + '.fin')
# can remove .out and .err files as hopefully that information was directed somewhere else (eg. log file)
for id in job_id_list:
    if os.path.isfile(str(id) + ".err"):
        os.remove(str(id) + ".err")
    if os.path.isfile(str(id) + ".out"):
        os.remove(str(id) + ".out")

## makes a final completion file that indicates daily fits have been completed
completefile = os.path.join('.', latest_directory + '.fin')
file = open(completefile, "w") 
file.close()

time.sleep(60)

## final permissions update
for root, dirs, files in os.walk(os.path.join("/panfs/roc/groups/7/cough052/shared/ztfrest/candidate_fits",latest_directory,"")):
    for d in dirs:
        os.chmod(os.path.join(root, d), 0o774)
    for f in files:
        os.chmod(os.path.join(root, f), 0o774)

## Sync files with schoty at conclusion of fitting and pushes to slack

time.sleep(60)
subprocess.run("rsync -av /home/cough052/shared/ztfrest/candidate_fits ztfrest@schoty.caltech.edu:/scr2/ztfrest/ZTF/ztfrest", shell=True, capture_output=True)
time.sleep(60)
## would like to make it so slackBot runs after each object finishes its fits, but that likely requires some reworking of the while loop
if args.slackBot:
    subprocess.run("ssh ztfrest@schoty.caltech.edu bash /scr2/ztfrest/ZTF/ztfrest/nmma_slack_bot.sh", shell=True, capture_output=True)
