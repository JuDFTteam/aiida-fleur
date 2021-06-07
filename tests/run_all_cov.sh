#!/usr/bin/env sh
export AIIDA_PATH='.';
mkdir -p '.aiida';
#pytest -sv
#pytest -v
pytest --cov-report=xml --cov=aiida_fleur --cov=tests
#pytest --cov-report=html --cov=aiida_fleur
#pytest --cov-report=html --cov=aiida_fleur -vv -rXxs -x

# to create badge (requires coverage-badge)
#coverage-badge -o coverage.svg

# pylint (for shield create, by hand, or write script to write total into svg) 
# pylint ../../aiida_fleur/ > outlint
