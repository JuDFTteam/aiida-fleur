#!/bin/bash
# Run or submit all workflow tests
# parse as argument the fleur and inpgen code you want to use, optional options, if non default for the used machine, 
# if a number is parsed only that run test is launched. --submit will submit all

# the materials and all other parameter are definded in the submission tests...


FLEUR_CODE=7652 #iff
FLEUR_CODE2=1596 # claix
FLEUR_CODE3=4892 #4892 dev 4260 release# JURECA
INPGEN_CODE=7550 # iff
STRUCTURE=138 #1604
SUBMIT=true
REMOTE=1921 #Tungesten on iff003
FLEURINP=1916 # Tungesten
OPTIONS=4129 # claix
OPTIONS3=4272 # JURECA 1 node full mpi
OPTIONS4=4286 # JURECA 1 node 4 mpi 6 openmp
SPTIONS1=49278 #iff
#OPTIONS5
REMOTE2=1921 # W on claix

# on iff

verdi run test_submit_scf.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
verdi run test_submit_eos.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
verdi run test_submit_initial_cls.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT
verdi run test_submit_corehole.py --fleur $FLEUR_CODE --inpgen $INPGEN_CODE --structure $STRUCTURE --submit $SUBMIT

#verdi run test_submit_dos.py --fleur $FLEUR_CODE --fleurinp $FLEURINP --remote $REMOTE --submit $SUBMIT
#verdi run test_submit_band.py --fleur $FLEUR_CODE --fleurinp $FLEURINP --remote $REMOTE --submit $SUBMIT



# on claix

#verdi run test_submit_scf.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_eos.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_initial_cls.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_corehole.py --fleur $FLEUR_CODE2 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS --submit $SUBMIT

#verdi run test_submit_dos.py --fleur $FLEUR_CODE2 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_band.py --fleur $FLEUR_CODE2 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS --submit $SUBMIT


# on jureca

#verdi run test_submit_scf.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS3 --submit $SUBMIT
#verdi run test_submit_scf.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT
#verdi run test_submit_eos.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT
#verdi run test_submit_initial_cls.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT
#verdi run test_submit_corehole.py --fleur $FLEUR_CODE3 --inpgen $INPGEN_CODE --structure $STRUCTURE --options $OPTIONS4 --submit $SUBMIT

#verdi run test_submit_dos.py --fleur $FLEUR_CODE3 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS --submit $SUBMIT
#verdi run test_submit_band.py --fleur $FLEUR_CODE3 --fleurinp $FLEURINP --remote $REMOTE2 --options $OPTIONS --submit $SUBMIT



