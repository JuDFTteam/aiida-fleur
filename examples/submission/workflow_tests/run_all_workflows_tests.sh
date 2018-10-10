#!/bin/bash
# Run or submit all workflow tests
# parse as argument the fleur and inpgen code you want to use, optional options, if non default for the used machine, 
# if a number is parsed only that run test is launched. --submit will submit all

# the materials and all other parameter are definded in the submission tests...


FLEUR_CODE=1599 #iff
FLEUR_CODE2=1596 # claix
FLEUR_CODE3=4892 #4892 dev 4260 release# JURECA
FLEUR_CODE4=5345 # jureca Booster
INPGEN_CODE=1598 # mac
STRUCTURE=1604
STRUCTURE=50875 # from Philipp
SUBMIT=true
REMOTE=1921 #Tungesten on iff003
FLEURINP=1916 # Tungesten
OPTIONS=49361 # claix
OPTIONS3=4272 # JURECA 1 node full mpi
OPTIONS4=49504 ## JURECA 1 node 4 mpi 6 openmp
OPTIONS5=49319 # JURECA BOOSTER 8 mpi 8 openmp
SPTIONS1=49278 #iff
#OPTIONS5
REMOTE2=1921 # W on claix

# on iff

#verdi run test_submit_scf.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
#verdi run test_submit_eos.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
#verdi run test_submit_initial_cls.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
#verdi run test_submit_corehole.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT

#verdi run test_submit_dos.py --fleur $FLEUR_CODE --fleurinp $FLEURINP --remote $REMOTE --submit $SUBMIT
#verdi run test_submit_band.py --fleur $FLEUR_CODE --fleurinp $FLEURINP --remote $REMOTE --submit $SUBMIT



# on claix

verdi run test_submit_scf.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_eos.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_initial_cls.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_corehole.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT

#verdi run test_submit_dos.py --fleur $FLEUR_CODE2 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_band.py --fleur $FLEUR_CODE2 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS --submit $SUBMIT


# on jureca

#verdi run test_submit_scf.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS3 --submit $SUBMIT
verdi run test_submit_scf.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT
#verdi run test_submit_eos.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT
#verdi run test_submit_initial_cls.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT
#verdi run test_submit_corehole.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT

#verdi run test_submit_dos.py --fleur $FLEUR_CODE3 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS4 --submit $SUBMIT
#verdi run test_submit_band.py --fleur $FLEUR_CODE3 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS4 --submit $SUBMIT


# on jureca booster

#verdi run test_submit_scf.py --fleur $FLEUR_CODE4 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS5 --submit $SUBMIT
#verdi run test_submit_scf.py --fleur $FLEUR_CODE4 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS5 --submit $SUBMIT
#verdi run test_submit_eos.py --fleur $FLEUR_CODE4 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS5 --submit $SUBMIT
#verdi run test_submit_initial_cls.py --fleur $FLEUR_CODE4 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS5 --submit $SUBMIT
#verdi run test_submit_corehole.py --fleur $FLEUR_CODE4 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS5 --submit $SUBMIT

#verdi run test_submit_dos.py --fleur $FLEUR_CODE4 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS5 --submit $SUBMIT
#verdi run test_submit_band.py --fleur $FLEUR_CODE4 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS5 --submit $SUBMIT



