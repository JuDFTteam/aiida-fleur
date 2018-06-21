#!/bin/bash
# Run or submit all workflow tests
# parse as argument the fleur and inpgen code you want to use, optional options, if non default for the used machine, 
# if a number is parsed only that run test is launched. --submit will submit all

# the materials and all other parameter are definded in the submission tests...


FLEUR_CODE=1599
INPGEN_CODE=1598
STRUCTURE=1604
SUBMIT=True


verdi run test_submit_scf.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
verdi run test_submit_eos.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
