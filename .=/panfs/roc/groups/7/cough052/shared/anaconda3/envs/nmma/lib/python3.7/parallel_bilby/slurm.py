from os.path import abspath

from .parser import create_analysis_parser
from .utils import get_cli_args


def setup_submit(data_dump_file, inputs, args):
    # Create analysis nodes
    analysis_nodes = []
    for idx in range(args.n_parallel):
        node = AnalysisNode(data_dump_file, inputs, idx, args)
        node.write()
        analysis_nodes.append(node)

    if len(analysis_nodes) > 1:
        final_analysis_node = MergeNodes(analysis_nodes, inputs, args)
        final_analysis_node.write()
    else:
        final_analysis_node = analysis_nodes[0]

    bash_script = f"{inputs.submit_directory}/bash_{inputs.label}.sh"
    with open(bash_script, "w+") as ff:
        dependent_job_ids = []
        for ii, node in enumerate(analysis_nodes):
            print(f"jid{ii}=$(sbatch {node.filename})", file=ff)
            dependent_job_ids.append(f"${{jid{ii}##* }}")
        if len(analysis_nodes) > 1:
            print(
                f"sbatch --dependency=afterok:{':'.join(dependent_job_ids)} "
                f"{final_analysis_node.filename}",
                file=ff,
            )
        print('squeue -u $USER -o "%u %.10j %.8A %.4C %.40E %R"', file=ff)

    return bash_script


class BaseNode(object):
    def get_lines(self):
        lines = ["#!/bin/bash"]
        lines.append(f"#SBATCH --job-name={self.job_name}")
        if self.nodes > 1:
            lines.append(f"#SBATCH --nodes={self.nodes}")
        if self.ntasks_per_node > 1:
            lines.append(f"#SBATCH --ntasks-per-node={self.ntasks_per_node}")
        lines.append(f"#SBATCH --time={self.time}")
        if self.args.mem_per_cpu is not None:
            lines.append(f"#SBATCH --mem-per-cpu={self.mem_per_cpu}")
        lines.append(f"#SBATCH --output={self.logs}/{self.job_name}.log")
        if self.args.slurm_extra_lines is not None:
            slurm_extra_lines = " ".join(
                [f"--{lin}" for lin in self.args.slurm_extra_lines.split()]
            )
            for line in slurm_extra_lines.split():
                lines.append(f"#SBATCH {line}")
        lines.append("")
        if self.args.extra_lines:
            for line in self.args.extra_lines.split(";"):
                lines.append(line.strip())
        lines.append("")
        return lines

    def get_contents(self):
        lines = self.get_lines()
        return "\n".join(lines)

    def write(self):
        content = self.get_contents()
        with open(self.filename, "w+") as f:
            print(content, file=f)


class AnalysisNode(BaseNode):
    def __init__(self, data_dump_file, inputs, idx, args):
        self.data_dump_file = data_dump_file
        self.inputs = inputs
        self.args = args
        self.idx = idx
        self.filename = (
            f"{self.inputs.submit_directory}/"
            f"analysis_{self.inputs.label}_{self.idx}.sh"
        )
        self.job_name = f"{self.idx}_{self.inputs.label}"
        self.nodes = self.args.nodes
        self.ntasks_per_node = self.args.ntasks_per_node
        self.time = self.args.time
        self.mem_per_cpu = self.args.mem_per_cpu
        self.logs = self.inputs.data_analysis_log_directory

        # This are the defaults: used only to figure out which arguments to use
        analysis_parser = create_analysis_parser(sampler=self.args.sampler)
        self.analysis_args, _ = analysis_parser.parse_known_args(args=get_cli_args())
        # hack -- in the above the parse_known_arg sets the position param (ini) as
        # the data dump
        self.analysis_args.data_dump = self.data_dump_file

    @property
    def executable(self):
        if self.args.sampler == "dynesty":
            return "parallel_bilby_analysis"
        elif self.args.sampler == "ptemcee":
            return "parallel_bilby_ptemcee_analysis"
        else:
            raise ValueError(
                f"Unable to determine sampler to use from {self.args.sampler}"
            )

    @property
    def label(self):
        return f"{self.inputs.label}_{self.idx}"

    @property
    def output_filename(self):
        return (
            f"{self.inputs.result_directory}/{self.inputs.label}_{self.idx}_result.json"
        )

    def get_contents(self):
        lines = self.get_lines()
        lines.append('export MKL_NUM_THREADS="1"')
        lines.append('export MKL_DYNAMIC="FALSE"')
        lines.append("export OMP_NUM_THREADS=1")
        lines.append(f"export MPI_PER_NODE={self.args.ntasks_per_node}")
        lines.append("")

        run_string = self.get_run_string()
        lines.append(f"mpirun {self.executable} {run_string}")
        return "\n".join(lines)

    def get_run_string(self):
        run_list = [f"{self.data_dump_file}"]
        for key, val in vars(self.analysis_args).items():
            if key in ["data_dump", "label", "outdir", "sampling_seed"]:
                continue
            input_val = getattr(self.args, key)
            if val != input_val:
                if input_val is True:
                    # For flags only add the flag
                    run_list.append(f"--{key.replace('_', '-')}")
                else:
                    run_list.append(f"--{key.replace('_', '-')} {input_val}")

        run_list.append(f"--label {self.label}")
        run_list.append(f"--outdir {abspath(self.inputs.result_directory)}")
        run_list.append(f"--sampling-seed {self.inputs.sampling_seed + self.idx}")

        return " ".join(run_list)


class MergeNodes(BaseNode):
    def __init__(self, analysis_nodes, inputs, args):
        self.analysis_nodes = analysis_nodes

        self.inputs = inputs
        self.args = args
        self.job_name = f"merge_{self.inputs.label}"
        self.nodes = 1
        self.ntasks_per_node = 1
        self.time = "1:00:00"
        self.mem_per_cpu = "16GB"
        self.logs = self.inputs.data_analysis_log_directory

        self.filename = f"{self.inputs.submit_directory}/merge_{self.inputs.label}.sh"

    @property
    def file_list(self):
        return " ".join([node.output_filename for node in self.analysis_nodes])

    @property
    def merged_result_label(self):
        return f"{self.inputs.label}_merged"

    def get_contents(self):
        lines = self.get_lines()
        lines.append(
            f"bilby_result -r {self.file_list} "
            f"--merge "
            f"--label {self.merged_result_label} "
            f"--outdir {self.inputs.result_directory}"
        )
        return "\n".join(lines)
