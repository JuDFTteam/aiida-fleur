#!/bin/bash

#PBS -r n
#PBS -m n
#PBS -N aiida-None
#PBS -V
#PBS -o _scheduler-stdout.txt
#PBS -e _scheduler-stderr.txt
#PBS -q th123_node
#PBS -l nodes=1:ppn=12,walltime=00:03:00
cd "$PBS_O_WORKDIR"


'mpirun' '-np' '12' '/usr/users/iff_th1/broeder/codes/fleur_git_v2_7/iff003/fleur_iff003' '-xmlInput' '-wtime' '3' < 'inp.xml' > 'shell.out' 2> 'out.error'
