import argparse

import bilby
import bilby_pipe
from numpy import inf

from .utils import get_version_information

logger = bilby.core.utils.logger

__version__ = get_version_information()


def remove_argument_from_parser(parser, arg):
    for action in parser._actions:
        if action.dest == arg.replace("-", "_"):
            try:
                parser._handle_conflict_resolve(None, [("--" + arg, action)])
            except ValueError as e:
                logger.warning(f"Error removing {arg}: {e}")
    logger.debug(f"Request to remove arg {arg} from bilby_pipe args, but arg not found")


class StoreBoolean(argparse.Action):
    """argparse class for robust handling of booleans with configargparse

    When using configargparse, if the argument is setup with
    action="store_true", but the default is set to True, then there is no way,
    in the config file to switch the parameter off. To resolve this, this class
    handles the boolean properly.

    """

    def __call__(self, parser, namespace, value, option_string=None):
        value = str(value).lower()
        if value in ["true"]:
            setattr(namespace, self.dest, True)
        else:
            setattr(namespace, self.dest, False)


def _create_base_parser(sampler="dynesty"):
    base_parser = argparse.ArgumentParser("base", add_help=False)
    base_parser.add(
        "--version",
        action="version",
        version=f"%(prog)s={__version__}\nbilby={bilby.__version__}",
    )
    if sampler in ["all", "dynesty"]:
        base_parser = _add_dynesty_settings_to_parser(base_parser)
    if sampler in ["all", "ptemcee"]:
        base_parser = _add_ptemcee_settings_to_parser(base_parser)
    base_parser = _add_misc_settings_to_parser(base_parser)
    return base_parser


def _add_dynesty_settings_to_parser(parser):
    dynesty_group = parser.add_argument_group(title="Dynesty Settings")
    dynesty_group.add_argument(
        "-n", "--nlive", default=1000, type=int, help="Number of live points"
    )
    dynesty_group.add_argument(
        "--dlogz",
        default=0.1,
        type=float,
        help="Stopping criteria: remaining evidence, (default=0.1)",
    )
    dynesty_group.add_argument(
        "--n-effective",
        default=inf,
        type=float,
        help="Stopping criteria: effective number of samples, (default=inf)",
    )
    dynesty_group.add_argument(
        "--dynesty-sample",
        default="rwalk",
        type=str,
        help="Dynesty sampling method (default=rwalk). Note, the dynesty rwalk "
        "method is overwritten by parallel bilby for an optimised version ",
    )
    dynesty_group.add_argument(
        "--dynesty-bound",
        default="multi",
        type=str,
        help="Dynesty bounding method (default=multi)",
    )
    dynesty_group.add_argument(
        "--walks",
        default=100,
        type=int,
        help="Minimum number of walks, defaults to 100",
    )
    dynesty_group.add_argument(
        "--maxmcmc",
        default=5000,
        type=int,
        help="Maximum number of walks, defaults to 5000",
    )
    dynesty_group.add_argument(
        "--nact",
        default=5,
        type=int,
        help="Number of autocorrelation times to take, defaults to 5",
    )
    dynesty_group.add_argument(
        "--min-eff",
        default=10,
        type=float,
        help="The minimum efficiency at which to switch from uniform sampling.",
    )
    dynesty_group.add_argument(
        "--facc", default=0.5, type=float, help="See dynesty.NestedSampler"
    )
    dynesty_group.add_argument(
        "--vol-dec", default=0.5, type=float, help="See dynesty.NestedSampler"
    )
    dynesty_group.add_argument(
        "--vol-check", default=8, type=float, help="See dynesty.NestedSampler"
    )
    dynesty_group.add_argument(
        "--enlarge", default=1.5, type=float, help="See dynesty.NestedSampler"
    )
    dynesty_group.add_argument(
        "--n-check-point",
        default=100,
        type=int,
        help="Steps to take before attempting checkpoint",
    )
    dynesty_group.add_argument(
        "--max-its",
        default=10 ** 10,
        type=int,
        help="Maximum number of iterations to sample for (default=1.e10)",
    )
    dynesty_group.add_argument(
        "--max-run-time",
        default=1.0e10,
        type=float,
        help="Maximum time to run for (default=1.e10 s)",
    )
    dynesty_group.add_argument(
        "--fast-mpi",
        default=False,
        type=bool,
        help="Fast MPI communication pattern (default=False)",
    )
    dynesty_group.add_argument(
        "--mpi-timing",
        default=False,
        type=bool,
        help="Print MPI timing when finished (default=False)",
    )
    dynesty_group.add_argument(
        "--mpi-timing-interval",
        default=0,
        type=int,
        help="Interval to write timing snapshot to disk (default=0 -- disabled)",
    )
    dynesty_group.add_argument(
        "--nestcheck",
        default=False,
        action="store_true",
        help=(
            "Save a 'nestcheck' pickle in the outdir (default=False). "
            "This pickle stores a `nestcheck.data_processing.process_dynesty_run` "
            "object, which can be used during post processing to compute the "
            "implementation and bootstrap errors explained by Higson et al (2018) "
            "in “Sampling Errors In Nested Sampling Parameter Estimation”."
        ),
    )
    return parser


def _add_ptemcee_settings_to_parser(parser):
    ptemcee_group = parser.add_argument_group(title="PTEmcee Settings")
    ptemcee_group.add_argument(
        "--nsamples", default=10000, type=int, help="Number of samples to draw"
    )
    ptemcee_group.add_argument(
        "--ntemps", default=20, type=int, help="Number of temperatures"
    )
    ptemcee_group.add_argument(
        "--nwalkers", default=100, type=int, help="Number of walkers"
    )
    ptemcee_group.add_argument(
        "--max-iterations",
        default=100000,
        type=int,
        help="Maximum number of iterations",
    )
    ptemcee_group.add_argument(
        "--ncheck", default=500, type=int, help="Period with which to check convergence"
    )
    ptemcee_group.add_argument(
        "--burn-in-nact",
        default=50.0,
        type=float,
        help="Number of autocorrelation times to discard for burn-in",
    )
    ptemcee_group.add_argument(
        "--thin-by-nact",
        default=1.0,
        type=float,
        help="Thin-by number of autocorrelation times",
    )
    ptemcee_group.add_argument(
        "--frac-threshold",
        default=0.01,
        type=float,
        help="Threshold on the fractional change in ACT required for convergence",
    )
    ptemcee_group.add_argument(
        "--nfrac",
        default=5,
        type=int,
        help="The number of checks passing the frac-threshold for convergence",
    )
    ptemcee_group.add_argument(
        "--min-tau",
        default=30,
        type=int,
        help="The minimum tau to accept: used to prevent early convergence",
    )
    ptemcee_group.add_argument(
        "--Tmax",
        default=10000,
        type=float,
        help="The maximum temperature to use, default=10000",
    )
    ptemcee_group.add_argument(
        "--safety",
        default=1.0,
        type=float,
        help="Multiplicitive safety factor on the estimated tau",
    )
    ptemcee_group.add_argument(
        "--autocorr-c",
        default=5.0,
        type=float,
        help="The step size for the window search when calculating tau. Default: 5",
    )
    ptemcee_group.add_argument(
        "--autocorr-tol",
        default=50.0,
        type=float,
        help=(
            "The minimum number of autocorrelations needs to trust the"
            " autocorrelation estimate. Default: 0 (always return a result)"
        ),
    )
    ptemcee_group.add_argument(
        "--adapt",
        default=False,
        action="store_true",
        help=(
            "If ``True``, the temperature ladder is dynamically adapted as "
            "the sampler runs to achieve uniform swap acceptance ratios "
            "between adjacent chains.  See `arXiv:1501.05823 "
            "<http://arxiv.org/abs/1501.05823>`_ for details."
        ),
    )
    return parser


def _add_misc_settings_to_parser(parser):
    misc_group = parser.add_argument_group(title="Misc. Settings")
    misc_group.add_argument(
        "--bilby-zero-likelihood-mode", default=False, action="store_true"
    )
    misc_group.add_argument(
        "--sampling-seed",
        type=bilby_pipe.utils.noneint,
        default=None,
        help="Random seed for sampling, parallel runs will be incremented",
    )
    misc_group.add_argument(
        "-c", "--clean", action="store_true", help="Run clean: ignore any resume files"
    )
    misc_group.add_argument(
        "--no-plot",
        action="store_true",
        help="If true, don't generate check-point plots",
    )
    misc_group.add_argument(
        "--do-not-save-bounds-in-resume",
        default=False,
        action="store_true",
        help=(
            "If true, do not store bounds in the resume file. This can make "
            "resume files large (~GB)"
        ),
    )
    misc_group.add_argument(
        "--check-point-deltaT",
        default=3600,
        type=float,
        help="Write a checkpoint resume file and diagnostic plots every deltaT [s].",
    )
    misc_group.add_argument(
        "--rotate-checkpoints",
        action="store_true",
        help="If true, backup checkpoint before overwriting (ending in '.bk').",
    )
    return parser


def _add_slurm_settings_to_parser(parser):
    slurm_group = parser.add_argument_group(title="Slurm Settings")
    slurm_group.add_argument(
        "--nodes", type=int, required=True, help="Number of nodes to use"
    )
    slurm_group.add_argument(
        "--ntasks-per-node", type=int, required=True, help="Number of tasks per node"
    )
    slurm_group.add_argument(
        "--time",
        type=str,
        default="24:00:00",
        required=True,
        help="Maximum wall time (defaults to 24:00:00)",
    )
    slurm_group.add_argument(
        "--mem-per-cpu",
        type=str,
        default=None,
        help="Memory per CPU (defaults to None)",
    )
    slurm_group.add_argument(
        "--extra-lines",
        type=str,
        default=None,
        help="Additional lines, separated by ';', use for setting up conda env ",
    )
    slurm_group.add_argument(
        "--slurm-extra-lines",
        type=str,
        default=None,
        help="additional slurm args (args that need #SBATCH in front) of the form arg=val separated by sapce",
    )
    return parser


def _create_reduced_bilby_pipe_parser():
    bilby_pipe_parser = bilby_pipe.parser.create_parser()
    bilby_pipe_arguments_to_ignore = [
        "version",
        "accounting",
        "local",
        "local-generation",
        "local-plot",
        "request-memory",
        "request-memory-generation",
        "request-cpus",
        "singularity-image",
        "scheduler",
        "scheduler-args",
        "scheduler-module",
        "scheduler-env",
        "transfer-files",
        "online-pe",
        "osg",
        "email",
        "postprocessing-executable",
        "postprocessing-arguments",
        "sampler",
        "sampling-seed",
        "sampler-kwargs",
        "plot-calibration",
        "plot-corner",
        "plot-format",
        "plot-marginal",
        "plot-skymap",
        "plot-waveform",
    ]
    for arg in bilby_pipe_arguments_to_ignore:
        remove_argument_from_parser(bilby_pipe_parser, arg)

    bilby_pipe_parser.add_argument(
        "--sampler",
        choices=["dynesty", "ptemcee"],
        default="dynesty",
        type=str,
        help="The parallelised sampler to use, defaults to dynesty",
    )
    return bilby_pipe_parser


def create_generation_parser():
    """Parser for parallel_bilby_generation"""
    parser = _create_base_parser(sampler="all")
    bilby_pipe_parser = _create_reduced_bilby_pipe_parser()
    generation_parser = bilby_pipe.parser.BilbyArgParser(
        prog="parallel_bilby_generation",
        usage=__doc__,
        ignore_unknown_config_file_keys=False,
        allow_abbrev=False,
        parents=[parser, bilby_pipe_parser],
        add_help=False,
    )
    generation_parser = _add_slurm_settings_to_parser(generation_parser)
    return generation_parser


def create_analysis_parser(sampler="dynesty"):
    """Parser for parallel_bilby_analysis"""
    parser = _create_base_parser(sampler=sampler)
    analysis_parser = argparse.ArgumentParser(
        prog="parallel_bilby_analysis", parents=[parser]
    )
    analysis_parser.add_argument(
        "data_dump",
        type=str,
        help="The pickled data dump generated by parallel_bilby_analysis",
    )
    analysis_parser.add_argument(
        "--outdir", default=None, type=str, help="Outdir to overwrite input label"
    )
    analysis_parser.add_argument(
        "--label", default=None, type=str, help="Label to overwrite input label"
    )
    return analysis_parser
