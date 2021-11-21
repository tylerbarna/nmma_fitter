#!/bin/bash
#SBATCH --job-name=BarebonesCreateInjections
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ztfrest@gmail.com
#SBATCH --time=11:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8gb
#SBATCH -p small
#SBATCH -o ./logs/%j.out
#SBATCH -e ./logs/%j.err
 
 cd /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/
 
 source /panfs/roc/groups/7/cough052/barna314/anaconda3/bin/activate nmma
 
 python /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/injectionScript.py --prior-file "$1" --eos-file /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/ALF2.dat --n-injection "$2" --binary-type BNS --outfolder "$3" --label testLC --model Bu2019lm --svd-path /panfs/roc/groups/7/cough052/shared/NMMA/svdmodels/ --filters g,r,i --injection-detection-limit 22,22,22 --cpus 4 --tar
 
 chmod -R 774 /panfs/roc/groups/7/cough052/barna314/nmma_fitter/injection/
 
 