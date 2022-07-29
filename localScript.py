import subprocess
import os
import sys
import time
import glob
import argparse

import numpy as np

from datetime import date
#from fit_utils import parse_csv ## not used here

## Goal of this script is to manually execute model fits of specific csv files and save the results to a folder.

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

og_directory = os.getcwd()

if not args.dataDir:
    print("Please pass --dataDir")
    sys.exit()

if not args.candidate:
    print("Please pass --candidate")
    sys.exit()

if not args.models:
    print("Please pass --models")
    sys.exit()

model_list = args.models

job_name = {"Bu2019lm": "KNjob.txt",
            "TrPi2018": "GRBjob.txt",
            "nugent-hyper": "SNjob.txt",
            "Piro2021": "SCjob.txt",}

outdir = os.path.join(os.getcwd(), "local_output/")
if not os.path.exists(outdir):
    os.makedirs(outdir)

## No check on the number of detections, making assumption that all submissions have a requisite number of detections since this is a manually executed script

## No logging system or slack bot (yet?)



