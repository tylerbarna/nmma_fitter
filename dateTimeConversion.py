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

from astropy.timeseries import TimeSeries as ts
from astropy.time import Time

df = pd.read_csv('msiStats/statsDataframe.csv',index_col=0).fillna(value=np.nan)
print(df.describe())
#print(df['day'])

## get day column and split based on the - character
startDay, stopDay = df['day'].str.split('-', 1).str
startDay, stopDay = startDay.astype('float'), stopDay.astype('float')

print(startDay)

## convert to astropy time
startDate, stopDate = Time(startDay, format='jd').datetime64, Time(stopDay, format='jd').datetime64
print(startDate)
df['startDate'] = startDate
df['stopDate'] = stopDate

df.to_csv('msiStats/statsDataframePrime.csv')
