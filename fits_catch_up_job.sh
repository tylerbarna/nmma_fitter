#!/bin/bash
#SBATCH --job-name=catch_up_fits
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --time=47:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8gb
#NOTSBATCH -p small
#SBATCH -o ./logs/%j.out
#SBATCH -e ./logs/%j.err


cd /home/cough052/barna314/nmma_fitter/

source /home/cough052/barna314/anaconda3/bin/activate nmma

python /home/cough052/barna314/nmma_fitter/catch_up.py