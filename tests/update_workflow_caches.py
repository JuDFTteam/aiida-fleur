"""
Update the workflow caches and calculations
from an artifact (extracted) containing the tests folder
"""
import shutil
import sys
from pathlib import Path
import os
import subprocess

file_path = Path(__file__).parent.resolve()

path = Path(sys.argv[1])
if not path.exists():
    raise FileNotFoundError(path)

print("Removing previous results:")
shutil.rmtree(os.fspath(file_path / 'workflows' / 'caches'))
shutil.rmtree(os.fspath(file_path / 'workflows' / 'calculations'))

print("Copying new results")
shutil.copytree(os.fspath(path / 'tests' / 'workflows' / 'caches'),
                os.fspath(file_path / 'workflows' / 'caches'))

shutil.copytree(os.fspath(path / 'tests' / 'workflows' / 'calculations'),
                os.fspath(file_path / 'workflows' / 'calculations'))

subprocess.run(["pre-commit", "run", "--all-files"], check=False)