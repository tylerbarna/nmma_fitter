import datetime
import os
import sys
import timeit

import bilby
import numpy as np
from bilby.gw import conversion

logger = bilby.core.utils.logger


def get_cli_args():
    """Tool to get CLI args (also makes testing easier)"""
    return sys.argv[1:]


def get_version_information():
    version_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "parallel_bilby/.version"
    )
    try:
        with open(version_file, "r") as f:
            return f.readline().rstrip()
    except EnvironmentError:
        print("No version information file '.version' found")


def fill_sample(args):
    ii, sample, likelihood = args
    sample = dict(sample).copy()
    marg_params = likelihood.parameters.copy()
    likelihood.parameters.update(sample)
    sample.update(likelihood.get_sky_frame_parameters())
    sample = likelihood.generate_posterior_sample_from_marginalized_likelihood()
    # Likelihood needs to have marg params to calculate correct SNR
    likelihood.parameters.update(marg_params)
    conversion.compute_snrs(sample, likelihood)
    sample = conversion._generate_all_cbc_parameters(
        sample,
        likelihood.waveform_generator.waveform_arguments,
        conversion.convert_to_lal_binary_black_hole_parameters,
    )
    return sample


def get_initial_point_from_prior(args):
    """
    Draw initial points from the prior subject to constraints applied both to
    the prior and the likelihood.

    We remove any points where the likelihood or prior is infinite or NaN.

    The `log_likelihood_function` often converts infinite values to large
    finite values so we catch those.
    """
    (
        prior_transform_function,
        log_prior_function,
        log_likelihood_function,
        ndim,
        calculate_likelihood,
    ) = args
    bad_values = [np.inf, np.nan_to_num(np.inf), np.nan]
    while True:
        unit = np.random.rand(ndim)
        theta = prior_transform_function(unit)
        if abs(log_prior_function(theta)) not in bad_values:
            if calculate_likelihood:
                logl = log_likelihood_function(theta)
                if abs(logl) not in bad_values:
                    return unit, theta, logl
            else:
                return unit, theta, np.nan


def get_initial_points_from_prior(
    ndim,
    npoints,
    prior_transform_function,
    log_prior_function,
    log_likelihood_function,
    pool,
    calculate_likelihood=True,
):
    args_list = [
        (
            prior_transform_function,
            log_prior_function,
            log_likelihood_function,
            ndim,
            calculate_likelihood,
        )
        for i in range(npoints)
    ]
    initial_points = pool.map(get_initial_point_from_prior, args_list)
    u_list = [point[0] for point in initial_points]
    v_list = [point[1] for point in initial_points]
    l_list = [point[2] for point in initial_points]

    return np.array(u_list), np.array(v_list), np.array(l_list)


def safe_file_dump(data, filename, module):
    """Safely dump data to a .pickle file

    Parameters
    ----------
    data:
        data to dump
    filename: str
        The file to dump to
    module: pickle, dill
        The python module to use
    """

    temp_filename = filename + ".temp"
    with open(temp_filename, "wb") as file:
        module.dump(data, file)
    os.rename(temp_filename, filename)


def stopwatch(method):
    """A decorator that logs the time spent in a function"""

    def timed(*args, **kw):
        t_start = timeit.time.perf_counter()
        result = method(*args, **kw)
        t_end = timeit.time.perf_counter()
        duration = datetime.timedelta(seconds=t_end - t_start)
        logger.info(f"{method.__name__}: {duration}")
        return result

    return timed
