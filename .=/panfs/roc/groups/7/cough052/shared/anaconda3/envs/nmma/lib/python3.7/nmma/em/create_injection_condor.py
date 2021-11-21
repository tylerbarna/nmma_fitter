import os
import argparse
import json
import pandas as pd

import numpy as np

import bilby
from bilby_pipe.create_injections import InjectionCreator

from subprocess import check_output

def main():

    parser = argparse.ArgumentParser(
        description="Slurm files from nmma injection file"
    )
    parser.add_argument("--model", type=str, required=True, help="Name of the kilonova model to be used")
    parser.add_argument(
        "--prior-file",
        type=str,
        required=True,
        help="The prior file from which to generate injections"
    )
    parser.add_argument(
        "--injection-file",
        type=str,
        required=True,
        help="The bilby injection json file to be used"
    )
    parser.add_argument(
        "--condor-dag-file",
        type=str,
        required=True,
        help="The condor dag file to be created"
    )
    parser.add_argument(
        "--condor-sub-file",
        type=str,
        required=True,
        help="The condor sub file to be created"
    )
    parser.add_argument(
        "--bash-file",
        type=str,
        required=True,
        help="The bash file to be created"
    )
    parser.add_argument(
        "-o", "--outdir",
        type=str,
        default="outdir"
    )
    args = parser.parse_args()

    # load the injection json file
    if args.injection_file:
        if args.injection_file.endswith('.json'):
            with open(args.injection_file, 'rb') as f:
                injection_data = json.load(f)
                datadict = injection_data['injections']['content']
                dataframe_from_inj = pd.DataFrame.from_dict(datadict)
        else:
            print("Only json supported.")
            exit(1)

    if len(dataframe_from_inj) > 0:
        args.n_injection = len(dataframe_from_inj)

    # create the injection dataframe from the prior_file
    injection_creator = InjectionCreator(
        prior_file=args.prior_file,
        prior_dict=None,
        n_injection=args.n_injection,
        default_prior="PriorDict",
        gps_file=None,
        trigger_time=0,
        generation_seed=0,
    )
    dataframe_from_prior = injection_creator.get_injection_dataframe()

    # combine the dataframes
    dataframe = pd.DataFrame.merge(
        dataframe_from_inj, dataframe_from_prior,
        how='outer',
        left_index=True, right_index=True
    )

    lc_analysis = check_output(["which", "light_curve_analysis"]).decode().replace("\n","")

    logdir = os.path.join(args.outdir,'logs')
    if not os.path.isdir(logdir):
        os.makedirs(logdir)

    job_number = 0
    fid = open(args.condor_dag_file, "w")
    fid1 = open(args.bash_file, "w")
    for index, row in dataframe.iterrows():
        #with open(args.analysis_file, 'r') as file:
        #    analysis = file.read()

        outdir = os.path.join(args.outdir, str(index))
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        priors = bilby.gw.prior.PriorDict(args.prior_file)
        priors.to_file(outdir, label="injection")
        priorfile = os.path.join(outdir, "injection.prior")
        injfile = os.path.join(outdir, "lc.csv")

        fid.write('JOB %d %s\n'%(job_number, args.condor_sub_file))
        fid.write('RETRY %d 3\n'%(job_number))
        fid.write('VARS %d jobNumber="%d" PRIOR="%s" OUTDIR="%s" INJOUT="%s" INJNUM="%s"\n'%(job_number, job_number, priorfile, outdir, injfile, str(index)))
        fid.write('\n\n')
        job_number = job_number + 1

        fid1.write('%s --model %s --svd-path /home/%s/gwemlightcurves/output/svdmodels --outdir %s --label injection_%s --prior analysis.prior --tmin 0 --tmax 20 --dt 0.5 --error-budget 1 --nlive 256 --Ebv-max 0 --injection %s --injection-num %s --injection-detection-limit 24.1,25.0,25.0,25.3,24.5,23.0,23.2,22.6,22.6 --injection-outfile %s --generation-seed 42 --filters u,g,r,i,z,y,J,H,K --plot --remove-nondetections\n' % (lc_analysis, args.model, os.environ["USER"], outdir, args.model, args.injection_file, str(index), injfile))

    fid.close()

    fid = open(args.condor_sub_file, "w")
    fid.write('executable = %s\n' % lc_analysis)
    fid.write(f'output = {logdir}/out.$(jobNumber)\n')
    fid.write(f'error = {logdir}/err.$(jobNumber)\n')
    fid.write('arguments = --model %s --svd-path /home/%s/gwemlightcurves/output/svdmodels --outdir $(OUTDIR) --label injection_%s --prior analysis.prior --tmin 0 --tmax 20 --dt 0.5 --error-budget 1 --nlive 256 --Ebv-max 0 --injection %s --injection-num $(INJNUM) --injection-detection-limit 24.1,25.0,25.0,25.3,24.5,23.0,23.2,22.6,22.6 --injection-outfile $(INJOUT) --generation-seed 42 --filters u,g,r,i,z,y,J,H,K --plot --remove-nondetections\n' % (args.model, os.environ["USER"], args.model, args.injection_file))
    fid.write('requirements = OpSys == "LINUX"\n')
    fid.write('request_memory = 8192\n')
    fid.write('request_cpus = 1\n')
    fid.write('accounting_group = ligo.dev.o2.burst.allsky.stamp\n')
    fid.write('notification = nevers\n')
    fid.write('getenv = true\n')
    fid.write('log = /local/%s/light_curve_analysis.log\n' % os.environ["USER"])
    fid.write('+MaxHours = 24\n')
    fid.write('universe = vanilla\n')
    fid.write('queue 1\n')

if __name__ == "__main__":
    main()
