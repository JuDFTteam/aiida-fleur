#!/usr/bin/env sh
export AIIDA_PATH=$(pwd);
mkdir -p '.aiida';
#pytest -sv
#pytest -v
pytest --mpl $@
