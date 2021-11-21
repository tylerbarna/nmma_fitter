import os

import pandas as pd
import numpy as np
from astropy.time import Time

from nmma.em.model import SVDLightCurveModel, GRBLightCurveModel, KilonovaGRBLightCurveModel, SupernovaGRBLightCurveModel, SupernovaLightCurveModel, ShockCoolingLightCurveModel

# Useful functions used by nmma_fit.py

def get_bestfit_lightcurve(model,
                           posterior_file,
                           svd_path,
                           sample_times,
                           joint_light_curve=False,
                           mag_ncoeff=10,
                           lbol_ncoeff=10,
                           grb_resolution=7,
                           jet_type=0):
    ''' Generates the bestfit lightcurve model
    par model The name of the model used in fitting.
    par posterior_file Location and name of the posterior sample file
    par svd_path Path containing model svd files.
    par sample_times Grid over which the model is evaluated.

    returns 2-tuple (dictionary of bestfit parameters, bestfit model magnitudes)
    '''
    #instead of posterior_file, should it be given the candidate
    #name?

    #################
    # Setup the model
    #################
    kilonova_kwargs = dict(model=model, svd_path=svd_path, mag_ncoeff=mag_ncoeff, lbol_ncoeff=lbol_ncoeff, parameter_conversion=None)
    if joint_light_curve:

        assert model != 'TrPi2018', "TrPi2018 is not a kilonova / supernova model"

        if model != 'nugent-hyper':

            kilonova_kwargs = dict(model=model, svd_path=svd_path,
                                   mag_ncoeff=mag_ncoeff,
                                   lbol_ncoeff=lbol_ncoeff,
                                   parameter_conversion=None)

            bestfit_model = KilonovaGRBLightCurveModel(sample_times=sample_times,
                                                           kilonova_kwargs=kilonova_kwargs,
                                                           GRB_resolution=grb_resolution,
                                                           jetType=jet_type)

        else:

            bestfit_model = SupernovaGRBLightCurveModel(sample_times=sample_times,
                                                            GRB_resolution=grb_resolution,
                                                            jetType=jet_type)

    else:
        if model == 'TrPi2018':
            bestfit_model = GRBLightCurveModel(sample_times=sample_times, resolution=grb_resolution, jetType=jet_type)
        elif model == 'nugent-hyper':
            bestfit_model = SupernovaLightCurveModel(sample_times=sample_times)
        elif model == 'Piro2021':
            bestfit_model = ShockCoolingLightCurveModel(sample_times=sample_times)
        else:
            light_curve_kwargs = dict(model=model, sample_times=sample_times,
                                      svd_path=svd_path, mag_ncoeff=mag_ncoeff,
                                      lbol_ncoeff=lbol_ncoeff)
            bestfit_model = SVDLightCurveModel(**light_curve_kwargs)

    ##########################
    # Fetch bestfit parameters
    ##########################
    posterior_samples = pd.read_csv(posterior_file, header=0, delimiter=' ')
    bestfit_idx = np.argmax(posterior_samples.log_likelihood.to_numpy())
    bestfit_params = posterior_samples.to_dict(orient='list')
    for key in bestfit_params.keys():
        bestfit_params[key] = bestfit_params[key][bestfit_idx]

    #########################
    # Generate the lightcurve
    #########################
    _, mag = bestfit_model.generate_lightcurve(sample_times, bestfit_params)
    for filt in mag.keys():
        mag[filt] += 5. * np.log10(bestfit_params['luminosity_distance'] * 1e6 / 10.)
    mag['bestfit_sample_times'] = sample_times
    bestfit_lightcurve_mag = pd.DataFrame.from_dict(mag)

    return(bestfit_params, bestfit_lightcurve_mag)

# Parses a file format with a single candidate
def parse_csv(infile,
              candname,
              outdir = './candidate_data/'):
    #process the numeric data
    in_data = np.genfromtxt(infile, dtype=None, delimiter=',', skip_header = 1, encoding = None)

    # Candidates are given keys that address a 2D array with
    # photometry data
    out_data = []

    for line in np.atleast_1d(in_data):
        #extract time and put in isot format
        time = Time(line[1], format='jd').isot

        filter = line[4]

        magnitude = line[2]

        error = line[3]

        if 99.0 == magnitude:
            magnitude = line[5]
            error = np.inf

        out_data.append([str(time), filter, str(magnitude), str(error)])

    os.makedirs(outdir, exist_ok = True)

    # output the data
    # in the format desired by NMMA
    out_file = open(outdir + candname + ".dat", 'w')
    for line in out_data:
        out_file.write(line[0] + " " + line[1] + " " + line[2] + " " + line[3] + "\n")
    out_file.close()

    return out_data
