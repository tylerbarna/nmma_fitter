import argparse
import json
import os
import subprocess
import sys

## goal of this would be to generate the job script using the settings.json file and then delete it after the job is submitted

parser = argparse.ArgumentParser()
parser.add_argument("-m","--model",type=str,default=None)
parser.add_argument("-t","--fit_trigger_time",action="store_true")
args = parser.parse_args()

model = args.model



config = json.load(open('settings.json'))



f = open('job.sh','a')

f.write('#!/bin/bash'+'\n')
f.write

