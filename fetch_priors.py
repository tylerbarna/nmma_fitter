## Note: Currently doesn't work (return() can only be used in a function)
import subprocess
import sys
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-p","--prior", type=str, default=None)
parser.add_argument("-m","--model",type=str,default=None)
parser.add_argument("-t","--fit_trigger_time",action="store_true")
args = parser.parse_args()

prior = args.prior
model = args.model
fit_trigger_time = args.fit_trigger_time

if prior == None:
    if model == 'nugent-hyper':
        # SN
        if fit_trigger_time:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_sn_t0.prior'
        else:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_sn.prior'
    elif model == 'TrPi2018':
        # GRB
        if fit_trigger_time:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_grb_t0.prior'
        else:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_grb.prior'
    elif model == 'Piro2021':
        # Shock cooling
        if fit_trigger_time:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_sc_t0.prior'
        else:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_sc.prior'
    elif model == 'Bu2019lm':
        # KN
        if fit_trigger_time:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_kn_t0.prior'
        else:
            prior = '/panfs/roc/groups/7/cough052/barna314/nmma_fitter/priors/ZTF_kn.prior'
    else:
        print("nmma_fit.py does not know of the prior file for model ", model)
        exit(1)

return(prior)

## This script generally pulls out some of the bulk from nmma_fit.py but isn't yet implemented in
## that script. Ultimate goal would be to add functionality that allows for realtime addition of 
## new priors to the script in an easy to read format - would potentially occur when this 
## repo's functionality is merged with nmma general
