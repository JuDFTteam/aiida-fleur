#!/bin/bash

#copy plugin files from aiida_fleur into your aiida version

aiida_repo=/usr/users/iff_th1/broeder/aiida/aiida/aiida
aiida_corelevel=${PWD}
#'.'

#test if aiida_repo exists
if [ ! -d $aiida_repo ]; then
    echo $aiida_repo 'does not exists, write in the script the aiida head directory -> exit'
    exit 1
fi

echo 'copying files from' $aiida_corelevel 'to' $aiida_repo


#tools
if [ ! -d $aiida_repo/tools/codespecific/fleur ]; then
    mkdir $aiida_repo/tools/codespecific/fleur
    echo 'created dir' $aiida_repo/tools/codespecific/fleur
fi
cp $aiida_corelevel/workflows/*.py $aiida_repo/tools/codespecific/fleur/
cp $aiida_corelevel/util/*.py $aiida_repo/tools/codespecific/fleur/

