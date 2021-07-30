#!/bin/bash
#SBATCH --job-name=schotyPull
#SBATCH --time=11:59:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8gb
#SBATCH -p amdsmall
#SBATCH -o ./logs/%j.out
#SBATCH -e ./logs/%j.err

rsync -aOv --no-perms ztfrest@schoty.caltech.edu:/scr2/ztfrest/ZTF/ztfrest/candidates /home/cough052/shared/ztfrest
chmod -R 777 /home/cough052/shared/ztfrest/

