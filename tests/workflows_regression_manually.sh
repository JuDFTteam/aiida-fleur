#!/bin/bash
# Todo: parse as argument the fleur and inpgen code you want to use, optional options, if non default for the used machine, 
#
# This test set should be executed at least once before a release
# It runs all launch commands form the aiida-fleur cmdline once
# with defaults for a given inpgen or fleur code or it use
# the materials and all other parameter are definded in the submission tests...

FLEUR=713 #iff pc
INPGEN='497d15d9-9e53-434a-9b32-b85256fe3a69' #712 # iff pc
STRUCTURE=1604
SUBMIT=true
FLEURINP=1916 # Tungesten
OPTIONS=49361 # claix
REMOTE=1921 # W on claix

# import a some nodes needed for the regression tests
verdi import ./files/exports/base_export_regression_tests.tar.gz

# Run or submit all workflows via CLI

aiida-fleur launch inpgen --inpgen $INPGEN 
aiida-fleur launch fleur --fleur $FLEUR -P $REMOTE 
aiida-fleur launch scf --inpgen $INPGEN --fleur $FLEUR
aiida-fleur launch eos --inpgen $INPGEN --fleur $FLEUR
#aiida-fleur launch banddos
aiida-fleur launch relax --inpgen $INPGEN --fleur $FLEUR
#aiida-fleur launch corehole
#aiida-fleur launch init_cls
