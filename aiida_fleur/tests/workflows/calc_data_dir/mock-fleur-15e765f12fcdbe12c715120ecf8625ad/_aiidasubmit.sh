#!/bin/bash
exec > _scheduler-stdout.txt
exec 2> _scheduler-stderr.txt
env --ignore-environment \



'/Users/broeder/codes/aiida/fleur/max_r4/serial/fleur'  '-minimalOutput' '-wtime' '5.0'  > 'shell.out' 2> 'out.error'