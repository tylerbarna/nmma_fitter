#!/bin/bash
#SBATCH --job-name=manual_nmma_fitter
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --time=23:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#NOTSBATCH -p small
#SBATCH -o ./logs/%j.out
#SBATCH -e ./logs/%j.err

cd /home/cough052/barna314/nmma_fitter/

python /home/cough052/barna314/nmma_fitter/make_jobs.py --slackBot --models Bu2019lm nugent-hyper TrPi2018 Piro2021 --dataDir ./candidate_data/alerts --outdir ./candidate_data/alert_fits --force

chmod -R 777 /home/cough052/barna314/nmma_fitter/logs/