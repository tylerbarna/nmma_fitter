#!/bin/bash

#SBATCH --time=07:59:59
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#NOTSBATCH -p amdsmall
#SBATCH -o %j.out
#SBATCH -e %j.err

source /home/cough052/barna314/anaconda3/bin/activate nmma

python /panfs/roc/groups/7/cough052/barna314/nmma_fitter/nmma_fit.py --datafile "$1" --candname "$2" --model "$3" --dataDir "$4" --nlive 512 --cpus 2
