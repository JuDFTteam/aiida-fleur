# -*- coding: utf-8 -*-
'''
This small dirty scripts helps to migrate aiida exports files produced by tests
prob works only under linux. cleans data_dir, workflows/caches
'''
import os
import shutil
#import subprocess

#base = '/home/broeder/aiida/github/judft/aiida-fleur/aiida_fleur/tests/'
data_dirs = ['data_dir/', 'workflows/caches/']

for dirs in data_dirs:
    listing = os.listdir(dirs)
    for infile in listing:
        print('migrating aiida export file: ' + dirs + infile)
        infile_old = 'old_' + infile
        shutil.move(dirs + infile, dirs + infile_old)
        #subprocess.run(["", "])
        os.system('verdi export migrate {} {}'.format(dirs + infile_old, dirs + infile))
        #os.system("ls {} {}".format(dirs+infile_old, dirs+infile))
