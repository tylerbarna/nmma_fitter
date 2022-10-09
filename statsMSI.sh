#!/bin/bash

#SBATCH --time=07:59:59
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH -p amdsmall
#SBATCH -o ./msiStats/%j.out
#SBATCH -e ./msiStats/%j.err

source /home/cough052/shared/anaconda3/bin/activate nmma

python /panfs/roc/groups/7/cough052/barna314/nmma_fitter/stats.py -c /panfs/roc/groups/7/cough052/shared/ztfrest/candidates/partnership -f /panfs/roc/groups/7/cough052/shared/ztfrest/candidate_fits -o ./msiStats --verbose
