#!/bin/bash --login
#SBATCH --job-name=test                # name of the run
#SBATCH --output=test.log              # logfile of the run
#SBATCH --nodes=1                      # Run on a single computer
#SBATCH --ntasks=1                     # Run a single task        
#SBATCH --cpus-per-task=16             # Number of CPU cores per task
#SBATCH --mem=128G                     # Job memory request
#SBATCH --time=200:00:00                # Time limit hrs:min:sec
#SBATCH --mail-type=BEGIN,END,FAIL     # Send email on begin, end, and fail
#SBATCH --mail-user=zongmin.yu@campus.tu-berlin.de   # Your email address


module load java/21

java -Xmx120G -Xms120G -cp matsim-berlin-6.4-v6.0-350-g04d23cd-dirty.jar org.matsim.run.OpenBerlinScenario run --10pct --config

chmod 770 -R .
