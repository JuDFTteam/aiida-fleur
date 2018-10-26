#!/bin/bash

# Be verbose, and stop with error as soon there's one
set -ev

# Needed on Jenkins
#if [ -e ~/.bashrc ] ; then source ~/.bashrc ; fi

case "$TEST_TYPE" in
    docs)
        # Compile the docs (HTML format);
        # -C change to 'docs' directory before doing anything
        # -n to warn about all missing references
        # -W to convert warnings in errors
        #SPHINXOPTS="-nW" make html -C docs
        make html
        ;;
    tests)
        # make sure we have the correct pg_ctl in our path for pgtest, to prevent issue #1722
        # this must match the version request in travis.yml
       cd ./aiida_fleur/tests/ && ./run_all_cov.sh
esac
