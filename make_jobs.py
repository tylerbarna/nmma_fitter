import subprocess
import os
import sys
import glob
import time

import numpy as np

from datetime import date
from fit_utils import parse_csv

# print current date for log
#today = date.today()
#print("Current Date: ",str(today.strftime("%m-%d-%Y"))

# Search directory and create a fit job for each

candidate_directory = "/panfs/roc/groups/7/cough052/shared/ztfrest/candidates/partnership"
latest_directory = max([f for f in os.listdir(candidate_directory)], key=lambda x: os.stat(os.path.join(candidate_directory,x)).st_mtime)
search_directory = os.path.join(candidate_directory,latest_directory,"") 
print("Candidate Directory: "+str(search_directory))
og_directory = os.getcwd()


# -TODO- List of jobs? Dictionary of jobs so they can be different for different models?
job_name = {"Bu2019lm": "/panfs/roc/groups/7/cough052/barna314/nmma_fitter/KNjob.txt",
            "TrPi2018": "/panfs/roc/groups/7/cough052/barna314/nmma_fitter/GRBjob.txt",
            "nugent-hyper": "/panfs/roc/groups/7/cough052/barna314/nmma_fitter/SNjob.txt"}

# List of models to run.
model_list = ["Bu2019lm", "TrPi2018", "nugent-hyper"]

# Outdirectory

os.chdir("/panfs/roc/groups/7/cough052/shared/ztfrest/candidates/candidate_fits")
outdir = os.path.join("./",latest_directory,"")
if not os.path.isdir(outdir):
    os.makedirs(outdir)
    #subprocess.run("chmod -r 777 "+outdir)
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
        command = subprocess.run("sbatch " + job_name[model] + " " + file_list[ii] + " " + candidate_names[ii] + " " + model, shell=True, capture_output=True)
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
while len(live_jobs) > 0:
    time.sleep(60)

    finished_jobs = []
    for id, (candname, model) in live_jobs.items():
        # nmma_fit makes a .fin file when done
        if os.path.isfile(candname + "_" + model + ".fin"):
            # Do something now that we know the job is done
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


## final permissions update
for root, dirs, files in os.walk(os.path.join("/panfs/roc/groups/7/cough052/shared/ztfrest/candidates/partnership/candidate_data",latest_directory,"")):
    for d in dirs:
        os.chmod(os.path.join(root, d), 0o774)
    for f in files:
        os.chmod(os.path.join(root, f), 0o774)

