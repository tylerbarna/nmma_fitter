import subprocess
import os
import sys
import glob
import time
import argparse

import numpy as np
import pandas as pd

from astropy.time import Time
from datetime import datetime

parser = argparse.ArgumentParser(description='Convert fritz files to the csv and dat files expected by the pipeline')
parser.add_argument('-f','--fritz_file', type=str, help='path to fritz file')
## note: this is assumed to be the csv from the "show photometry table" element, not the "export bold light curve to csv" element.
## the latter does not seem to export magnitudes from ztf as expected (it exports the fluxes though)
## File should have columns: "obj_id", "ra", "dec", "filter", "mjd", "snr", "instrument_id", "instrument_name", "ra_unc", "dec_unc", "origin", "id", "altdata", "annotation", "mag", "magerr", "magsys", "limiting_mag", "Delete"
parser.add_argument('--id', type=str, help='name of the object (e.g. ZTF20abwysqy)')
parser.add_argument('--instrument', nargs="+", type=str, default = ['ZTF'], help='name of the instrument(s)')
parser.add_argument('-o','--output_dir', type=str, default='./', help='path to output directory')
args = parser.parse_args()

## read in the fritz file
df = pd.read_csv(args.fritz_file)

## filter out the non-ztf data (could potentally allow for other instruments in the future)
## columns are in order of appearance in nmma formatted csv file (can be found in nmma_fitter repo in pipelineStructureExample)
## example file: https://github.com/tylerbarna/nmma_fitter/blob/main/candidate_data/pipelineStructureExample/candidates/partnership/2459778-2459785/lc_ZTF22aatuvld_forced1_stacked0.csv

df = df[df['instrument_name'].isin(args.instrument)] ## filter out non-instrument data 

df2 = pd.DataFrame() ## create clean dataframe with only the columns we want
df2['jd'] = df['mjd'] + 2400000.5
df2['mag'] = df['mag']
df2['mag_unc'] = df['magerr']
df2['filter'] = df['filter'].map(lambda x: str(x).replace('ztf','')) ## remove the ztf prefix from the filter name (so it's just g,r,i)
df2['limmag'] = df['limiting_mag']
df2.replace(np.nan, 99, regex=True, inplace=True) ## replace empty strings with 99
df2['programid'] = 1 ## not sure if this is important to include for the pipeline
df2['forced'] = 1
df2.loc[df2['limmag'] == 99, 'forced'] = 0 ## change forced to 0 if the limiting mag is 99

## now write the csv file
csv_filename = os.path.join(args.output_dir, 'lc_' + args.id + '_forced1_stacked0' + '.csv') ## example filename: lc_ZTF20abwysqy_forced1_stacked0.csv
df2.to_csv(csv_filename, index=True) ## index is included in expected format

## create the dat file
## columns are in order of appearance in nmma formatted dat file (can be found in nmma_fitter repo in pipelineStructureExample)
## this is output by the fitter, but useful to have in case one is running locally
## example file: https://github.com/tylerbarna/nmma_fitter/blob/main/candidate_data/pipelineStructureExample/candidate_fits/2459778-2459785/candidate_data/ZTF22aatuvld.dat

df3 = pd.DataFrame()
df3['isotime'] = df['mjd'].map(lambda x: Time(x, format='mjd').isot) ## convert mjd to isotime (86400 seconds in a day)
df3['filter'] = df['filter'].map(lambda x: str(x).replace('ztf',''))
df3['mag'] = df['mag']
df3['mag_unc'] = df['magerr']
df3.replace(np.nan, 99, regex=True, inplace=True) ## replace empty strings with 99

## now write the dat file
dat_filename = os.path.join(args.output_dir, args.id + '.dat') ## example filename: ZTF20abwysqy.dat
df3.to_csv(dat_filename, index=False, header=False, sep=' ') ## index is included in expected format




