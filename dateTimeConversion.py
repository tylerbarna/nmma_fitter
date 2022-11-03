import sys
from cProfile import label
import os
import argparse
import glob
import time
import json

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as dates

 
from astropy.time import Time

df = pd.read_csv('msiStats/statsDataframe.csv',index_col=0).fillna(value=np.nan)
print(df.describe())

df
