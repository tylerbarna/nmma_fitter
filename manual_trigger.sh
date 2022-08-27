#!/bin/bash
#SBATCH --job-name=manual_nmma_fitter
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --time=23:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH -p small
#SBATCH -o ./logs/%j.out
#SBATCH -e ./logs/%j.err

cd /panfs/roc/groups/7/cough052/barna314/nmma_fitter/

source /home/cough052/shared/anaconda3/bin/activate nmma

srun /panfs/roc/groups/7/cough052/barna314/nmma_fitter/primary_job.txt