import subprocess
import os
import sys
import glob
import time
import argparse

import numpy as np

from datetime import date
from fit_utils import parse_csv

dataDirectory = "/panfs/roc/groups/7/cough052/shared/ztfrest/candidates/partnership"
dataFolders = [f.name for f in os.scandir(dataDirectory) if f.is_dir()]

fitDirectory = "/panfs/roc/groups/7/cough052/shared/ztfrest/candidate_fits"
fitFolders = [f.name for f in os.scandir(fitDirectory) if f.is_dir()]

## array of the directories present in data folder that haven't been fit yet
unfitData = np.setdiff1d(dataFolders, fitFolders)

## to-do: make it also check that all models have been run

for folder in unfitData:
    subprocess.run("python /panfs/roc/groups/7/cough052/barna314/nmma_fitter/make_jobs.py -d "  + folder, shell=True, capture_output=True)