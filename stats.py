## Essentially intended to be a way to create some nice stats plots for the paper
## July 2021-July 2022: 1807 candidates, average of 4.36 candidates per day

from secrets import choice
import subprocess
import sys
import os
import argparse
import glob

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
parser.add_argument("-f","--fileDir", type=str, default=None)
parser.add_argument('')

dayList = glob.glob(args.fileDir + "*")

numCandidates = [len(glob.glob(day + "/*.csv")) for day in dayList]

candList = glob.glob(args.fileDir + "*/*.csv")

# with open(
# )
