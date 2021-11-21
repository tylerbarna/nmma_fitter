#!/usr/bin/env python
"""
Module to run parallel bilby using MPI and ptemcee
"""
import copy
import datetime
import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path

import bilby
import emcee
import matplotlib
import matplotlib.pyplot as plt
import mpi4py
import numpy as np
import pandas as pd
import ptemcee
import tqdm
from bilby.gw import conversion
from schwimmbad import MPIPool

from .parser import create_analysis_parser
from .utils import fill_sample, get_initial_points_from_prior

matplotlib.use("Agg")

mpi4py.rc.threads = False
mpi4py.rc.recv_mprobe = False

logger = bilby.core.utils.logger


def main():
    """Do nothing function to play nicely with MPI"""
    pass


def plot_walkers(walkers, nburn, parameter_labels, outdir, label):
    """Method to plot the trace of the walkers in an ensemble MCMC plot"""
    nwalkers, nsteps, ndim = walkers.shape
    idxs = np.arange(nsteps)
    fig, axes = plt.subplots(nrows=ndim, figsize=(6, 3 * ndim))
    scatter_kwargs = dict(lw=0, marker="o", markersize=1, alpha=0.05)
    for i, ax in enumerate(axes):
        ax.plot(
            idxs[: nburn + 1], walkers[:, : nburn + 1, i].T, color="r", **scatter_kwargs
        )
        ax.set_ylabel(parameter_labels[i])

    for i, ax in enumerate(axes):
        ax.plot(idxs[nburn:], walkers[:, nburn:, i].T, color="k", **scatter_kwargs)

    fig.tight_layout()
    filename = f"{outdir}/{label}_traceplot.png"
    fig.savefig(filename)
    plt.close(fig)


def plot_tau(tau_list_n, tau_list):
    fig, ax = plt.subplots()
    ax.plot(tau_list_n, tau_list, "-x")
    ax.set_xlabel("Iteration")
    ax.set_ylabel(r"$\langle \tau \rangle$")
    fig.savefig(f"{outdir}/{label}_tau.png")
    plt.close(fig)


def checkpoint(outdir, label, nsamples_effective, sampler):
    logger.info("Writing checkpoint and diagnostics")

    # Store the samples if possible
    if nsamples_effective > 0:
        filename = f"{outdir}/{label}_samples.txt"
        samples = sampler.chain[0, :, nburn : sampler.time : thin, :].reshape(
            (-1, ndim)
        )
        df = pd.DataFrame(samples, columns=sampling_keys)
        df.to_csv(filename, index=False, header=True, sep=" ")

    # Pickle the resume artefacts
    sampler_copy = copy.copy(sampler)
    del sampler_copy.pool
    sampler_copy._chain = sampler._chain[:, :, : sampler.time, :]
    sampler_copy._logposterior = sampler._logposterior[:, :, : sampler.time]
    sampler_copy._loglikelihood = sampler._loglikelihood[:, :, : sampler.time]
    sampler_copy._beta_history = sampler._beta_history[:, : sampler.time]
    data = dict(sampler=sampler_copy, tau_list=tau_list, tau_list_n=tau_list_n)
    with open(resume_file, "wb") as file:
        pickle.dump(data, file, protocol=4)
    del data, sampler_copy

    # Generate the walkers plot diagnostic
    plot_walkers(
        sampler.chain[0, :, : sampler.time, :], nburn, sampling_keys, outdir, label
    )

    # Generate the tau plot diagnostic
    plot_tau(tau_list_n, tau_list)

    logger.info("Finished writing checkpoint and diagnostics")


def print_progress(
    sampler,
    input_args,
    time_per_check,
    nsamples_effective,
    samples_per_check,
    passes,
    tau,
    tau_pass,
):
    # Setup acceptance string
    acceptance = sampler.acceptance_fraction[0, :]
    acceptance_str = f"{np.min(acceptance):1.2f}->{np.max(acceptance):1.2f}"

    # Setup tswap acceptance string
    tswap_acceptance_fraction = sampler.tswap_acceptance_fraction
    tswap_acceptance_str = (
        f"{np.min(tswap_acceptance_fraction):1.2f}->"
        f"{np.max(tswap_acceptance_fraction):1.2f}"
    )

    ave_time_per_check = np.mean(time_per_check[-3:])
    time_left = (
        (input_args.nsamples - nsamples_effective)
        * ave_time_per_check
        / samples_per_check
    )
    if time_left > 0:
        time_left = str(datetime.timedelta(seconds=int(time_left)))
    else:
        time_left = "waiting on convergence"

    convergence = "".join([["F", "T"][i] for i in passes])

    tau_str = str(tau)
    if tau_pass is False:
        tau_str = tau_str + "(F)"

    ncalls = f"{sampler.time * input_args.nwalkers * sampler.ntemps:1.1e}"
    eval_timing = f"{1000.0 * ave_time_per_check / evals_per_check:1.1f}ms/evl"
    samp_timing = f"{1000.0 * ave_time_per_check / samples_per_check:1.2f}ms/smp"

    print(
        f"{sampler.time}| "
        f"nc:{ncalls}| "
        f"a0:{acceptance_str}| "
        f"swp:{tswap_acceptance_str}| "
        f"n:{nsamples_effective}<{input_args.nsamples}| "
        f"tau:{tau_str}| "
        f"{eval_timing}| "
        f"{samp_timing}| "
        f"{convergence}",
        flush=True,
    )


def compute_evidence(sampler, outdir, label, nburn, thin, make_plots=True):
    """Computes the evidence using thermodynamic integration"""
    betas = sampler.betas
    # We compute the evidence without the burnin samples, but we do not thin
    lnlike = sampler.loglikelihood[:, :, nburn : sampler.time]
    mean_lnlikes = np.mean(np.mean(lnlike, axis=1), axis=1)

    mean_lnlikes = mean_lnlikes[::-1]
    betas = betas[::-1]

    if any(np.isinf(mean_lnlikes)):
        logger.warning(
            "mean_lnlikes contains inf: recalculating without"
            f" the {len(betas[np.isinf(mean_lnlikes)])} infs"
        )
        idxs = np.isinf(mean_lnlikes)
        mean_lnlikes = mean_lnlikes[~idxs]
        betas = betas[~idxs]

    lnZ = np.trapz(mean_lnlikes, betas)
    z1 = np.trapz(mean_lnlikes, betas)
    z2 = np.trapz(mean_lnlikes[::-1][::2][::-1], betas[::-1][::2][::-1])
    lnZerr = np.abs(z1 - z2)

    if make_plots:
        fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(6, 8))
        ax1.semilogx(betas, mean_lnlikes, "-o")
        ax1.set_xlabel(r"$\beta$")
        ax1.set_ylabel(r"$\langle \log(\mathcal{L}) \rangle$")
        min_betas = []
        evidence = []
        for i in range(int(len(betas) / 2.0)):
            min_betas.append(betas[i])
            evidence.append(np.trapz(mean_lnlikes[i:], betas[i:]))

        ax2.semilogx(min_betas, evidence, "-o")
        ax2.set_ylabel(
            r"$\int_{\beta_{min}}^{\beta=1}"
            + r"\langle \log(\mathcal{L})\rangle d\beta$",
            size=16,
        )
        ax2.set_xlabel(r"$\beta_{min}$")
        plt.tight_layout()
        fig.savefig(f"{outdir}/{label}_beta_lnl.png")

    return lnZ, lnZerr


os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["MKL_DYNAMIC"] = "0"
os.environ["MPI_PER_NODE"] = "16"

analysis_parser = create_analysis_parser(sampler="ptemcee")
input_args = analysis_parser.parse_args()

with open(input_args.data_dump, "rb") as file:
    data_dump = pickle.load(file)

ifo_list = data_dump["ifo_list"]
waveform_generator = data_dump["waveform_generator"]
waveform_generator.start_time = ifo_list[0].time_array[0]
args = data_dump["args"]
injection_parameters = data_dump.get("injection_parameters", None)

outdir = args.outdir
if input_args.outdir is not None:
    outdir = input_args.outdir
label = args.label
if input_args.label is not None:
    label = input_args.label

priors = bilby.gw.prior.PriorDict.from_json(data_dump["prior_file"])

logger.setLevel(logging.WARNING)
likelihood = bilby.gw.likelihood.GravitationalWaveTransient(
    ifo_list,
    waveform_generator,
    priors=priors,
    time_marginalization=args.time_marginalization,
    phase_marginalization=args.phase_marginalization,
    distance_marginalization=args.distance_marginalization,
    distance_marginalization_lookup_table=args.distance_marginalization_lookup_table,
    jitter_time=args.jitter_time,
)
logger.setLevel(logging.INFO)


def prior_transform_function(u_array):
    return priors.rescale(sampling_keys, u_array)


def log_likelihood_function(v_array):
    if input_args.bilby_zero_likelihood_mode:
        return 0

    log_prior = log_prior_function(v_array)
    if np.isinf(log_prior):
        return log_prior

    parameters = {key: v for key, v in zip(sampling_keys, v_array)}
    if priors.evaluate_constraints(parameters) > 0:
        likelihood.parameters.update(parameters)
        return likelihood.log_likelihood()
    else:
        return np.nan_to_num(-np.inf)


def log_prior_function(v_array):
    params = {key: t for key, t in zip(sampling_keys, v_array)}
    return priors.ln_prob(params)


sampling_keys = []
for p in priors:
    if isinstance(priors[p], bilby.core.prior.Constraint):
        continue
    if isinstance(priors[p], (int, float)):
        likelihood.parameters[p] = priors[p]
    elif priors[p].is_fixed:
        likelihood.parameters[p] = priors[p].peak
    else:
        sampling_keys.append(p)

# Setting marginalized parameters to their reference values
if likelihood.phase_marginalization:
    likelihood.parameters["phase"] = priors["phase"]
if likelihood.time_marginalization:
    likelihood.parameters["geocent_time"] = priors["geocent_time"]
if likelihood.distance_marginalization:
    likelihood.parameters["luminosity_distance"] = priors["luminosity_distance"]

with MPIPool() as pool:
    if not pool.is_master():
        pool.wait()
        sys.exit(0)
    POOL_SIZE = pool.size

    logger.info(f"Setting sampling seed = {input_args.sampling_seed}")
    np.random.seed(input_args.sampling_seed)

    logger.info("Using priors:")
    for key in priors:
        logger.info(f"{key}: {priors[key]}")

    ndim = len(sampling_keys)
    init_sampler_kwargs = dict(
        nwalkers=input_args.nwalkers,
        dim=ndim,
        ntemps=input_args.ntemps,
        Tmax=input_args.Tmax,
    )

    # Check for a resume file
    resume_file = f"{outdir}/{label}_checkpoint_resume.pickle"
    if os.path.isfile(resume_file) and os.stat(resume_file).st_size > 0:
        try:
            logger.info(f"Resume data {resume_file} found")
            with open(resume_file, "rb") as file:
                data = pickle.load(file)
            sampler = data["sampler"]
            tau_list = data["tau_list"]
            tau_list_n = data["tau_list_n"]
            sampler.pool = pool
            pos0 = None
            iterations = input_args.max_iterations  # - sampler.time
            logger.info(f"Resuming from previous run with time={sampler.time}")
        except Exception:
            raise ValueError(
                f"Unable to read resume file {resume_file}, please delete it and retry"
            )
    else:
        # Initialize resume file
        Path(resume_file).touch()

        logger.info(f"Initializing sampling points with pool size={POOL_SIZE}")
        p0_list = []
        for i in tqdm.tqdm(range(input_args.ntemps)):
            _, p0, _ = get_initial_points_from_prior(
                ndim,
                input_args.nwalkers,
                prior_transform_function,
                log_prior_function,
                log_likelihood_function,
                pool,
                calculate_likelihood=False,
            )
            p0_list.append(p0)
        pos0 = np.array(p0_list)
        iterations = input_args.max_iterations
        tau_list = []
        tau_list_n = []

        # Set up the sampler
        logger.info(
            f"Initialize ptemcee.Sampler with "
            f"{json.dumps(init_sampler_kwargs, indent=1, sort_keys=True)}"
        )
        sampler = ptemcee.Sampler(
            logl=log_likelihood_function,
            logp=log_prior_function,
            pool=pool,
            **init_sampler_kwargs,
        )

    logger.info(
        f"Starting sampling: "
        f"nsamples={input_args.nsamples}, "
        f"burn_in_nact={input_args.burn_in_nact}, "
        f"thin_by_nact={input_args.thin_by_nact}, "
        f"adapt={input_args.adapt}, "
        f"autocorr_c={input_args.autocorr_c}, "
        f"autocorr_tol={input_args.autocorr_tol}, "
        f"ncheck={input_args.ncheck}"
    )

    t0 = datetime.datetime.now()
    time_per_check = []

    evals_per_check = input_args.nwalkers * input_args.ntemps * input_args.ncheck

    for (pos0, lnprob, lnlike) in sampler.sample(
        pos0, iterations=iterations, adapt=input_args.adapt
    ):
        # Only check convergence every ncheck steps
        if sampler.time % input_args.ncheck:
            continue

        t0_internal = datetime.datetime.now()
        # Compute ACT tau for 0-temperature chains
        samples = sampler.chain[0, :, : sampler.time, :]
        taus = []
        for ii in range(input_args.nwalkers):
            for jj, key in enumerate(sampling_keys):
                if "recalib" in key:
                    continue
                try:
                    taus.append(
                        emcee.autocorr.integrated_time(
                            samples[ii, :, jj], c=input_args.autocorr_c, tol=0
                        )[0]
                    )
                except emcee.autocorr.AutocorrError:
                    taus.append(np.inf)

        # Apply multiplicitive safety factor
        tau = input_args.safety * np.mean(taus)

        if np.isnan(tau) or np.isinf(tau):
            logger.info(f"{sampler.time} | Unable to use tau={tau}")
            continue

        # Convert to an integer and store for plotting
        tau = int(tau)
        tau_list.append(tau)
        tau_list_n.append(sampler.time)

        # Calculate the effective number of samples available
        nburn = int(input_args.burn_in_nact * tau)
        thin = int(np.max([1, input_args.thin_by_nact * tau]))
        samples_per_check = input_args.ncheck * input_args.nwalkers / thin
        nsamples_effective = int(input_args.nwalkers * (sampler.time - nburn) / thin)

        # Calculate fractional change in tau from previous iteration
        frac = (tau - np.array(tau_list)[-input_args.nfrac - 1 : -1]) / tau
        passes = frac < input_args.frac_threshold

        # Calculate convergence boolean
        converged = input_args.nsamples < nsamples_effective
        converged &= np.all(passes)
        if sampler.time < tau * input_args.autocorr_tol or tau < input_args.min_tau:
            converged = False
            tau_pass = False
        else:
            tau_pass = True

        # Calculate time per iteration
        time_per_check.append((datetime.datetime.now() - t0).total_seconds())
        t0 = datetime.datetime.now()

        # Print an update on the progress
        print_progress(
            sampler,
            input_args,
            time_per_check,
            nsamples_effective,
            samples_per_check,
            passes,
            tau,
            tau_pass,
        )

        if converged:
            logger.info("Finished sampling")
            break

        # If a checkpoint is due, checkpoint
        last_checkpoint_s = time.time() - os.path.getmtime(resume_file)
        if last_checkpoint_s > input_args.check_point_deltaT:
            checkpoint(outdir, label, nsamples_effective, sampler)

    # Check if we reached the end without converging
    if sampler.time == input_args.max_iterations:
        raise ValueError(
            f"Failed to reach convergence by max_iterations={input_args.max_iterations}"
        )

    # Run a final checkpoint to update the plots and samples
    checkpoint(outdir, label, nsamples_effective, sampler)

    # Set up an empty result object
    result = bilby.core.result.Result(
        label=label, outdir=outdir, search_parameter_keys=sampling_keys
    )
    result.priors = priors
    result.nburn = nburn

    # Get 0-likelihood samples and store in the result
    samples = sampler.chain[0, :, :, :]  # nwalkers, nsteps, ndim
    # result.walkers = samples[:, : sampler.time :, :]
    result.samples = samples[:, nburn : sampler.time : thin, :].reshape((-1, ndim))
    loglikelihood = sampler.loglikelihood[
        0, :, nburn : sampler.time : thin
    ]  # nwalkers, nsteps
    result.log_likelihood_evaluations = loglikelihood.reshape((-1))
    result.samples_to_posterior()

    # Create and store the meta data and injection_parameters
    result.meta_data = data_dump["meta_data"]
    result.meta_data["command_line_args"] = vars(input_args)
    result.meta_data["command_line_args"]["sampler"] = "parallel_bilby_ptemcee"
    result.meta_data["config_file"] = vars(args)
    result.meta_data["data_dump"] = input_args.data_dump
    result.meta_data["sampler_kwargs"] = init_sampler_kwargs
    result.meta_data["likelihood"] = likelihood.meta_data
    result.meta_data["injection_parameters"] = injection_parameters
    result.injection_parameters = injection_parameters

    log_evidence, log_evidence_err = compute_evidence(
        sampler, outdir, label, nburn, thin
    )

    result.log_noise_evidence = likelihood.noise_log_likelihood()
    result.log_evidence = log_evidence
    result.log_bayes_factor = log_evidence - result.log_noise_evidence
    result.log_evidence_err = log_evidence_err
    result.sampling_time = np.sum(time_per_check)

    # Post-process the posterior
    posterior = result.posterior
    nsamples = len(posterior)
    logger.info(f"Using {nsamples} samples")
    posterior = conversion.fill_from_fixed_priors(posterior, priors)
    logger.info(
        "Generating posterior from marginalized parameters for"
        f" nsamples={len(posterior)}, POOL={pool.size}"
    )
    fill_args = [(ii, row, likelihood) for ii, row in posterior.iterrows()]
    samples = pool.map(fill_sample, fill_args)

    result.posterior = pd.DataFrame(samples)

    logger.debug("Updating prior to the actual prior")
    for par, name in zip(
        ["distance", "phase", "time"], ["luminosity_distance", "phase", "geocent_time"]
    ):
        if getattr(likelihood, f"{par}_marginalization", False):
            priors[name] = likelihood.priors[name]
    result.priors = priors

    if args.convert_to_flat_in_component_mass:
        try:
            result = bilby.gw.prior.convert_to_flat_in_component_mass_prior(result)
        except Exception as e:
            logger.warning(f"Unable to convert to the LALInference prior: {e}")

    logger.info(f"Saving result to {outdir}/{label}_result.json")
    result.save_to_file(extension="json")
    print(f"Sampling time = {datetime.timedelta(seconds=result.sampling_time)}s")
    print(result)
