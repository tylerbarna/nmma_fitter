#!/bin/bash
#SBATCH --job-name=BarebonesCreateInjections
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --time=199:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32gb
#SBATCH -p max
#SBATCH -o ./logs/%j.out
#SBATCH -e ./logs/%j.err
 
 cd /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/
 
 source /panfs/roc/groups/7/cough052/barna314/anaconda3/bin/activate nmma
 
 python /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/injectionScript.py --prior-file /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/barebones_test_prior.json --eos-file /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/ALF2.dat -n 100 --binary-type BNS -f /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/testSampleBarebones/injection.json --label testLC --model Bu2019lm --svd-path /panfs/roc/groups/7/cough052/shared/NMMA/svdmodels/ --filters g,r,i --injection-detection-limit 22,22,22 --outdir /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/testSampleBarebones/lightcurves --cpus 4
 
 chmod -R 774 /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/