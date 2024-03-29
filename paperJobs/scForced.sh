#!/bin/bash
#SBATCH --job-name=scForced
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

source /home/cough052/barna314/anaconda3/bin/activate nmma

cd /home/cough052/barna314/nmma_fitter/

light_curve_analysis --data ./candidate_data/paper_candidates/v2/candidate_data/ZTF20abwysqyForced.dat --model Piro2021 --svd-path svdmodels/ --outdir ./outdir/abwysqyForced_Piro2021 --label abwysqyForced_Piro2021 --prior ./priors/ZTF_sc.prior --trigger-time 59087.18740740741 --tmin 0.05 --nlive 128 --plot