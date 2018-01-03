#!/bin/bash

#copy plugin files from aiida_fleur into your aiida version

#aiida_repo=/Users/broeder/aiida/my_aiida_version/aiida/
aiida_repo=/usr/users/iff_th1/broeder/aiida/aiida/aiida/
aiida_fleur=${PWD}/aiida_fleur
#'.'

#test if aiida_repo exists
if [ ! -d $aiida_repo ]; then
    echo $aiida_repo 'does not exists, write in the script the aiida head directory -> exit'
    exit 1
fi

echo 'copying files from' $aiida_fleur 'to' $aiida_repo

# calculations
#test if fleur_inp folder exists otherwise create
if [ ! -d $aiida_repo/orm/calculation/job/fleur_inp ]; then
    mkdir $aiida_repo/orm/calculation/job/fleur_inp
    echo 'created dir' $aiida_repo/orm/calculation/job/fleur_inp
fi
cp $aiida_fleur/calculation/* $aiida_repo/orm/calculation/job/fleur_inp/

#fleur_schema
cp -r $aiida_fleur/fleur_schema $aiida_repo/orm/calculation/job/fleur_inp/

#parsers
if [ ! -d $aiida_repo/parsers/plugins/fleur_inp ]; then
    mkdir $aiida_repo/parsers/plugins/fleur_inp
    echo 'created dir' $aiida_repo/parsers/plugins/fleur_inp
fi
cp $aiida_fleur/parsers/* $aiida_repo/parsers/plugins/fleur_inp/


#data
if [ ! -d $aiida_repo/orm/data/fleurinp ]; then
    mkdir $aiida_repo/orm/data/fleurinp
    echo 'created dir' $aiida_repo/orm/data/fleurinp
fi
cp $aiida_fleur/data/* $aiida_repo/orm/data/fleurinp/

#tools
if [ ! -d $aiida_repo/tools/codespecific/fleur ]; then
    mkdir $aiida_repo/tools/codespecific/fleur
    echo 'created dir' $aiida_repo/tools/codespecific/fleur
fi
cp $aiida_fleur/tools/* $aiida_repo/tools/codespecific/fleur/

cp $aiida_fleur/util/* $aiida_repo/tools/codespecific/fleur/

#worklfows
# for now they are all kept together, but this will change
cp $aiida_fleur/workflows/* $aiida_repo/tools/codespecific/fleur/
