import subprocess
import sys
import os
import argparse
import json
import glob
import time

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import pickle

from json import dumps, loads, JSONEncoder, JSONDecoder

parser = argparse.ArgumentParser(description="conversion parameters")
parser.add_argument('--lc-directory',type=str,required=True,help='directory where lightcurves are located')
parser.add_argument('--id-number',type=str,default="0",help='starting number for lightcurve ID column')
parser.add_argument('--outfile',type=str,required=True,help='location to save .csv file')
args = parser.parse_args()

Start= time.time()
start = time.time()
files = glob.glob(os.path.join(args.lc_directory,"*.dat"))

print('number of lightcurves: %s' % str(len(files)))

lc_df = [pd.read_csv(f) for f in files]
end = time.time()
print('read files in %s seconds' % str(end - start))

#[lc_df[lightcurve]['lc'] = int(int(args.id-number)+lightcurve) for lightcurve in range(len(files))]

start = time.time()
for lightcurve in range(len(files)):
    lc_df[lightcurve]['lc_id'] = int(int(args.id_number)+lightcurve)
end = time.time()
print('added id column in %s seconds' % str(end - start))

start = time.time()
combined_df = pd.concat(lc_df,ignore_index=True)
end = time.time()
print('concatenated files in %s seconds' % str(end - start))
End = time.time()
print('average time per file: %s seconds' % str((End-Start)/len(files)))

combined_df.to_csv(args.outfile,index=False)

