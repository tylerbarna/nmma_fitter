import subprocess
import os
import sys
import glob
import time

import numpy as np

from fit_utils import parse_csv

# Search directory and create a fit job for each

search_directory = "./test_dir"

job_name = "job.txt"

# -TODO- hopefully this can be turned into a list and we can run multiple models, including the grb model
model = "Bu2019lm"

# -TODO- Can be replaced with something of the form 'filename.log'
log_filename = "fit.log"

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

    # -TODO- May want to eliminate shell=True. Apparently there are security holes associated with that.
    # Submit job
    command = subprocess.run("sbatch " + job_name + " " + file_list[ii] + " " + candidate_names[ii] + " " + model, shell=True, capture_output=True)
    output = command.stdout
    outerr = command.stderr

    # conver output to an actual string
    output = str(output, 'utf-8')

    # Job id is generally the last part of the job submission output
    job_id = int(output.split(' ')[-1])
    logfile = open(log_filename, "a")
    logfile.write("Submitted job for candidate %s. Job id: "%candidate_names[ii] + str(job_id) + "\n")
    logfile.close()

    job_id_list.append(job_id)
    live_jobs[candidate_names[ii]] = job_id

# Check on jobs every minute to see if they finished.
# -TODO- Can change the wait time to be reasonable for release
while len(live_jobs) > 0:
    time.sleep(60)

    finished_candidates = []
    for candname, id in live_jobs.items():
        # nmma_fit makes a .fin file when done
        if os.path.isfile(candname + "_" + model + ".fin"):
            # Do something now that we know the job is done
            logfile = open(log_filename, "a")
            logfile.write("Job " + str(id) + " for candidate " + candname + " completed. Produced the following output: \n")
            
            outfile = open(str(id) + ".out", 'r')
            logfile.write(outfile.read())
            outfile.close()

            logfile.close()

            finished_candidates.append(candname)
            # Check if there were errors?
        elif os.path.isfile(str(id) + ".err") and os.path.getsize(str(id) + ".err") != 0:
            logfile = open(log_filename, "a")
            logfile.write("Job " + str(id) + " for candidate " + candname + " encountered the following errors: \n")
            errorfile = open(str(id) + ".err", 'r')
            logfile.write(errorfile.read())
            errorfile.close()
            logfile.close()
            finished_candidates.append(candname)

    # update the live job list
    for candname in finished_candidates:
        del live_jobs[candname]

# cleanup: delete finish files and empty error files
for ii in range(len(file_list)):
    if os.path.isfile(candidate_names[ii] + "_" + model + '.fin'):
        os.remove(candidate_names[ii] + "_" + model + '.fin')
# can remove .out and .err files as hopefully that information was directed somewhere else (eg. log file)
for id in job_id_list:
    if os.path.isfile(str(id) + ".err"):
        os.remove(str(id) + ".err")
    if os.path.isfile(str(id) + ".out"):
        os.remove(str(id) + ".out")
