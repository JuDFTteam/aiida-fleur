#!/usr/bin/env sh
export AIIDA_PATH=$(pwd);
mkdir -p '.aiida';
pytest --mpl -vs $@
