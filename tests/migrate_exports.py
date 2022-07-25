'''
This small dirty scripts helps to migrate aiida exports files produced by tests
prob works only under linux. cleans data_dir, workflows/caches
'''
import os
import shutil
import subprocess

data_dirs = ['data_dir/', 'workflows/caches/']

for folder in data_dirs:
    for infile in os.listdir(folder):
        print('migrating aiida export file: ' + folder + infile)
        subprocess.run(['verdi', 'archive', 'migrate', folder + infile, '--in-place'], check=True)
