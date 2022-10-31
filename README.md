![nmma_fitter](nmma_fitter_image.png)

Realtime node-based lightcurve fitting using [NMMA](https://github.com/nuclear-multimessenger-astronomy/nmma).

To run, try:

sbatch primary_job.txt

Note that the job scripts may need editing depending on how your conda environment is setup.

Generally, in order for the above to execute correctly, one must modify most of the scripts since much of the current scripts assume the use of the msi computing cluster. I would recommend branching the repo in order to create versions of the scripts compatible with other systems. Reworking the scripts to create a more general version of the code is an ongoing effort.

# Pipeline

The current flow of the automated pipeline is as follows: 

1. The schoty system runs a crontab script to retreive ztf data that passes filtering requirements every morning, which is then stored on the schoty candidates directory.
2. schoty_pull.sh/primary_job.txt is executed every half hour on the msi cluster via a scrontab job, which just activates the environment and calls make_jobs.py. This script pulls the latest data from the schoty database and copies it to the local directory. If there is no new data, the script does nothing and exits. If there is new data, the make_jobs.py script then determines which files are new to fit and creates the job scripts for the new files.
3. make_jobs.txt creates jobs for each of the objects for each model defined. GRBjob.txt, KNjob.txt, SCjob.txt, and SNjob.txt all perform the same function, with the primary difference being the number of live points used in the fit and the cluster on which the job is executed (some models, like TrPi2018 (the GRB model), require more computational power to execute in a reasonable timeframe). This is probably an area in which the pipeline could be simplified since the *job.txt files are mostly redundant. 
4. make_jobs.txt then usess the *job.txt files to run nmma_fit.py. This script runs the light_curve_analysis function from the base nmma module. A handful of the arguments passed to light_curve_analysis are hardcoded in the script. From there, the best fits lightcurves are retreived using a function defined in the fit_utils.py script. fit_utils.py is just a file that defines a handful of useful functions used in various scripts in nmma_fitter, including the aforementioned function (get_bestfit_lightcurve) as well as parse_csv. This script is somewhat problematic for organization of the directory because, to my last recollection, it's somewhat awkward to import functions from a .py file located in a different directory, which limits the ability to organize some of the scripts. Regardless, get_bestfit_lightcurve takes the posterior_samples.dat file that is created by nmma and converts it into a more useful format for plotting. To that end, nmma_fit.py creates plots of the best fit of the lightcurve and a corner plot of the parameter space. 
5. Step 4 is executed in parallel for each of the objects that meet the filtering requirements and each of the models. While these execute, make_jobs.py will continue to check on the status of the jobs. When nmma_fit.py finishes running, it will create a .fin file for each instance. When make_jobs.py finds that all of the .fin files are present (or it hits a pre-defined timeout condition), it ends the loop and cleans up the output directory by removing all the .fin files. It creates a final .fin file to signal that all fits have been completed for the day. After that, it runs an rsync command to copy the output directory to the schoty database. 
6. If the slackbout flag is set, make_jobs.py will connect to schoty and execute the nmma_slack_bot.sh script, which sends the generated plots and their associated likelihoods to the nmma-slack-bot channel on the GROWTH MMA Slack. The make_jobs.py script exits and the msi script loops back to step 2 to check for new data until schoty retreives data the next day.  


# Current Models 

- [nugent-hyper](https://ui.adsabs.harvard.edu/abs/2005ApJ...624..880L/abstract): Supernova
- [TrPi2018](https://ui.adsabs.harvard.edu/abs/2018MNRAS.478L..18T/abstract): Gamma Ray Burst
- [Piro2021](https://arxiv.org/abs/2007.08543): Shock Cooling
- [Bu2019lm](https://arxiv.org/abs/1906.04205): Kilonova


