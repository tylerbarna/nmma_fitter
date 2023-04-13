#!/bin/bash

#SBATCH --time=00:29:59
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#NOTSBATCH -p amdsmall
#SBATCH -o ./msiStats/%j.out
#SBATCH -e ./msiStats/%j.err

source /home/cough052/shared/anaconda3/bin/activate nmma

python /home/cough052/barna314/nmma_fitter/stats.py -c /home/cough052/shared/ztfrest/candidates/partnership -f /home/cough052/shared/ztfrest/candidate_fits -o ./msiStats --verbose
