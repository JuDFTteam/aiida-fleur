.. _exit_codes:

Reference of Exit codes
=======================

.. _documentation: https://aiida.readthedocs.io/projects/aiida-core/en/latest/working/processes.html#exit-codes

AiiDA processes return a special object upon termination - an exit code. Basically, there are two
types of exit-codes: non-zero and zero ones. If a process returned a zero exit code it has finished
successfully. In contrast, non-zero exit code means there were a problem.

For example, there are 2 processes shown below:

.. code-block:: bash

    (aiidapy)$ verdi process list -a -p 1
       PK  Created    State             Process label             Process status
     ----  ---------  ----------------  ------------------------  ----------------------------------
       60  3m ago     ⏹ Finished [0]    FleurCalculation
       68  3m ago     ⏹ Finished [302]  FleurCalculation

The first calculation was successful and the second one failed and threw exit code 302, which
means it could not open one of the output files for some reason.

For more detailed information, see AiiDA `documentation`_.


Shared meanings
---------------

Since v3.0.0 the numbers below 400 have the same meaning in every workchain that uses them, so
a script can branch on the exit status without knowing which workchain produced it:

=========  ======================================================================
Code       Meaning
=========  ======================================================================
230        The ``wf_parameters`` dict contains an unknown key or an invalid value
231        The combination of input ports given is not legal for this workchain
233        A given ``Code`` node does not use the expected plugin
235        The requested ``inpxml_changes`` could not be applied
236        The modified ``inp.xml`` no longer validates against the FLEUR schema
334        The reference/parent SCF this workchain builds on failed
335        That reference calculation produced no remote folder to restart from
343        Every sub-calculation of a scan failed
344        Some, but not all, sub-calculations of a scan failed
345        A sub-SCF workchain failed
360        In-process input generation (pyfleur) failed
361        A FLEUR calculation failed
362        An SCF cycle did not reach its convergence criterion
=========  ======================================================================

Numbers at 346 and above that are not in this list, and everything from 380 up, are specific to
one workchain; see the full table. Codes below 230 are reserved by ``aiida-core`` and are not used
by aiida-fleur.

The list of all exit codes implemented in AiiDA-FLEUR:

+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| Exit code | Name                                         | Message                                                 | Thrown by              |
+===========+==============================================+=========================================================+========================+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | BandDos                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | CFCoeff                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | Corehole               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | CreateMagnetic         |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | CutoffConv             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | DMI                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | EOS                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | FSM                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | MAE                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | MAE Conv               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | OrbControl             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | Relax                  |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | RelaxTorque            |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | SCF                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | SSDisp                 |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 230       | ERROR_INVALID_INPUT_PARAM                    | Invalid workchain parameters.                           | SSDisp Conv            |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | BandDos                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | CFCoeff                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | Corehole               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | CreateMagnetic         |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | DMI                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | FSM                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | InitialCLS             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | MAE                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | OrbControl             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | SCF                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 231       | ERROR_INVALID_INPUT_CONFIG                   | Invalid input configuration.                            | SSDisp                 |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Invalid code node specified, check inpgen and fleur     | BandDos                |
|           |                                              | code nodes.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | The code provided is invalid, or not of the right kind. | Corehole               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Invalid code node specified, check inpgen and fleur     | DMI                    |
|           |                                              | code nodes.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Invalid code node specified, check inpgen and fleur     | FSM                    |
|           |                                              | code nodes.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Invalid code node specified, check inpgen and fleur     | Jij                    |
|           |                                              | code nodes.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Invalid code node specified, check inpgen and fleur     | MAE                    |
|           |                                              | code nodes.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Input codes do not correspond to fleur or inpgen        | OrbControl             |
|           |                                              | respectively.                                           |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Input codes do not correspond to fleur or inpgen        | SCF                    |
|           |                                              | respectively.                                           |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Invalid code node specified, check inpgen and fleur     | SSDisp                 |
|           |                                              | code nodes.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 233       | ERROR_INVALID_CODE_PROVIDED                  | Invalid code node specified, check inpgen and fleur     | Strain                 |
|           |                                              | code nodes.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | BandDos                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | CFCoeff                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Changing of the FLEURINP data went wrong, check log.    | Corehole               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | DMI                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | FSM                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | MAE                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | OrbControl             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | SCF                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 235       | ERROR_CHANGING_FLEURINPUT_FAILED             | Input file modification failed.                         | SSDisp                 |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | BandDos                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | CFCoeff                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | The FLEUR input file for the calculation did not        | Corehole               |
|           |                                              | validate.                                               |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | DMI                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after modifications.           | FSM                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | MAE                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | OrbControl             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | SCF                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 236       | ERROR_INVALID_INPUT_FILE                     | Input file was corrupted after user's modifications.    | SSDisp                 |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 240       | ERROR_NO_SUCCESSFUL_KMAX_RUN                 | No successful Kmax calculation available.               | CutoffConv             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 241       | ERROR_NO_SUCCESSFUL_KMESH_INPGEN_RUN         | Input generation failed for every k-mesh.               | CutoffConv             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 242       | ERROR_NO_SUCCESSFUL_KPOINT_RUN               | No successful k-point calculation available.            | CutoffConv             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 243       | ERROR_NO_SUCCESSFUL_SMEARING_RUN             | No successful smearing calculation available.           | CutoffConv             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 300       | ERROR_NO_RETRIEVED_FOLDER                    | No retrieved folder found.                              | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 300       | ERROR_NO_RETRIEVED_FOLDER                    | No retrieved folder found.                              | FleurinpgenCalculation |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 301       | ERROR_OPENING_OUTPUTS                        | One of the output files can not be opened.              | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 301       | ERROR_OPENING_OUTPUTS                        | One of the output files can not be opened.              | FleurinpgenCalculation |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 302       | ERROR_FLEUR_CALC_FAILED                      | FLEUR calculation failed for unknown reason.            | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 303       | ERROR_NO_OUTXML                              | XML output file was not found.                          | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 304       | ERROR_XMLOUT_PARSING_FAILED                  | Parsing of XML output file failed.                      | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 305       | ERROR_RELAX_PARSING_FAILED                   | Parsing of relax XML output file failed.                | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 306       | ERROR_NO_INPXML                              | XML input file was not found.                           | FleurinpgenCalculation |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 307       | ERROR_MISSING_RETRIEVED_FILES                | Some required files were not retrieved.                 | FleurinpgenCalculation |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 308       | ERROR_FLEURINPDATA_INPUT_NOT_VALID           | During parsing: FleurinpData could not be initialized,  | FleurinpgenCalculation |
|           |                                              | see log.                                                |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 309       | ERROR_FLEURINPDATA_NOT_VALID                 | During parsing: FleurinpData failed validation.         | FleurinpgenCalculation |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 310       | ERROR_NOT_ENOUGH_MEMORY                      | FLEUR calculation failed due to lack of memory.         | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 310       | ERROR_UNKNOWN_PROFILE                        | The profile {profile} is not known to the used inpgen   | FleurinpgenCalculation |
|           |                                              | code                                                    |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 311       | ERROR_VACUUM_SPILL_RELAX                     | FLEUR calculation failed because an atom spilled to     | FleurBase              |
|           |                                              | thevacuum during relaxation                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 311       | ERROR_VACUUM_SPILL_RELAX                     | FLEUR calculation failed because an atom spilled to     | FleurCalculation       |
|           |                                              | thevacuum during relaxation                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 311       | ERROR_VACUUM_SPILL_RELAX                     | FLEUR calculation failed because an atom spilled to     | Relax                  |
|           |                                              | thevacuum during relaxation                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 311       | ERROR_VACUUM_SPILL_RELAX                     | FLEUR calculation failed because an atom spilled to     | RelaxTorque            |
|           |                                              | thevacuum during relaxation                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 312       | ERROR_MT_RADII                               | FLEUR calculation failed due to MT overlap.             | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 313       | ERROR_MT_RADII_RELAX                         | Overlapping MT-spheres during relaxation.               | FleurBase              |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 313       | ERROR_MT_RADII_RELAX                         | Overlapping MT-spheres during relaxation.               | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 313       | ERROR_MT_RADII_RELAX                         | Overlapping MT-spheres during relaxation.               | Relax                  |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 313       | ERROR_MT_RADII_RELAX                         | Overlapping MT-spheres during relaxation.               | RelaxTorque            |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 314       | ERROR_DROP_CDN                               | Problem with cdn is suspected. Consider removing cdn    | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 315       | ERROR_INVALID_ELEMENTS_MMPMAT                | The LDA+U density matrix contains invalid elements.     | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 316       | ERROR_TIME_LIMIT                             | Calculation failed due to time limits.                  | FleurCalculation       |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 318       | ERROR_MISSING_DEPENDENCY                     | Calculation failed due to missing dependency ({name})   | FleurCalculation       |
|           |                                              | for given calculation.                                  |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 319       | ERROR_FLEUR_WITHOUT_HDF5                     | The FLEUR executable was compiled without HDF5 support. | FleurCalculation       |
|           |                                              | aiida-fleur requires a FLEUR built with HDF5.           |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 334       | ERROR_REFERENCE_CALCULATION_FAILED           | SCF calculation failed.                                 | BandDos                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 334       | ERROR_REFERENCE_CALCULATION_FAILED           | Reference calculation failed.                           | DMI                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 334       | ERROR_REFERENCE_CALCULATION_FAILED           | Reference calculation failed.                           | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 334       | ERROR_REFERENCE_CALCULATION_FAILED           | Reference calculation failed.                           | MAE                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 334       | ERROR_REFERENCE_CALCULATION_FAILED           | Reference calculation failed.                           | SSDisp                 |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 335       | ERROR_REFERENCE_CALCULATION_NOREMOTE         | Found no SCF calculation remote repository.             | BandDos                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 335       | ERROR_REFERENCE_CALCULATION_NOREMOTE         | Found no reference calculation remote repository.       | DMI                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 335       | ERROR_REFERENCE_CALCULATION_NOREMOTE         | Found no reference calculation remote repository.       | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 335       | ERROR_REFERENCE_CALCULATION_NOREMOTE         | Found no reference calculation remote repository.       | MAE                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 335       | ERROR_REFERENCE_CALCULATION_NOREMOTE         | Found no reference calculation remote repository.       | SSDisp                 |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 336       | ERROR_FORCE_THEOREM_FAILED                   | Force theorem calculation failed.                       | DMI                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 336       | ERROR_FORCE_THEOREM_FAILED                   | Force theorem calculation failed.                       | MAE                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 336       | ERROR_FORCE_THEOREM_FAILED                   | Force theorem calculation failed.                       | SSDisp                 |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 337       | ERROR_POSTPROCESSING_FAILED                  | Postprocessing of greensf.hdf failed.                   | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 338       | ERROR_GREENSF_CALCULATION_FAILED             | Green function calculation failed.                      | Jij                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 343       | ERROR_ALL_FSM_CALCS_FAILED                   | All FSM SCF calculations failed.                        | FSM                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 343       | ERROR_ALL_SQAS_FAILED                        | Convergence MAE calculation failed for all SQAs.        | MAE Conv               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 343       | ERROR_ALL_CONFIGS_FAILED                     | Convergence LDA+U calculation failed for all Initial    | OrbControl             |
|           |                                              | configurations.                                         |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 343       | ERROR_ALL_QVECTORS_FAILED                    | Convergence SSDisp calculation failed for all           | SSDisp Conv            |
|           |                                              | q-vectors.                                              |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 344       | ERROR_SOME_SQAS_FAILED                       | Convergence MAE calculation failed for some SQAs.       | MAE Conv               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 344       | ERROR_SOME_CONFIGS_FAILED                    | Convergence LDA+U calculation failed for some Initial   | OrbControl             |
|           |                                              | configurations.                                         |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 344       | ERROR_SOME_QVECTORS_FAILED                   | Convergence SSDisp calculation failed for some          | SSDisp Conv            |
|           |                                              | q-vectors.                                              |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 345       | ERROR_SCF_FAILED                             | Convergence scf workflow failed.                        | CFCoeff                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 345       | ERROR_SCF_FAILED                             | At least one of the SCF sub processes did not finish    | EOS                    |
|           |                                              | successfully.                                           |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 345       | ERROR_SCF_FAILED                             | SCF Workchains failed for some reason.                  | Relax                  |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 345       | ERROR_SCF_FAILED                             | An SCF Workchain failed for some reason.                | RelaxTorque            |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 346       | ERROR_IN_REFERENCE_CREATION                  | Something went wrong in the determiation what coreholes | Corehole               |
|           |                                              | to calculate, probably the input format was not         |                        |
|           |                                              | correct. Check log.                                     |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 347       | ERROR_REFERENCE_MISSING                      | Reference calculation missing for at least one element. | InitialCLS             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 350       | ERROR_DID_NOT_RELAX                          | Optimization cycle did not lead to convergence of       | Relax                  |
|           |                                              | forces.                                                 |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 350       | ERROR_DID_NOT_RELAX                          | Optimization cycle did not lead to convergence.         | RelaxTorque            |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 352       | ERROR_NO_RELAX_OUTPUT                        | Found no relaxed structure info in the output of SCF    | Relax                  |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 352       | ERROR_NO_RELAX_OUTPUT                        | Found no relaxed structure info in the output of SCF    | RelaxTorque            |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 353       | ERROR_NO_SCF_OUTPUT                          | Found no SCF output                                     | Relax                  |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 353       | ERROR_NO_SCF_OUTPUT                          | Found no SCF output                                     | RelaxTorque            |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 354       | ERROR_SWITCH_BFGS                            | Force is small, switch to BFGS                          | Relax                  |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 360       | ERROR_INPGEN_CALCULATION_FAILED              | Inpgen calculation FAILED, check output                 | Corehole               |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 360       | ERROR_INITIAL_INPGEN_FAILED                  | Initial input generation failed.                        | CutoffConv             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 360       | ERROR_INPGEN_CALCULATION_FAILED              | Inpgen calculation failed.                              | FSM                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 360       | ERROR_INPGEN_CALCULATION_FAILED              | Inpgen calculation failed.                              | OrbControl             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 360       | ERROR_INPGEN_CALCULATION_FAILED              | Inpgen calculation failed.                              | SCF                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 361       | ERROR_FLEUR_CALCULATION_FAILED               | At least one FLEUR calculation FAILED, check the output | Corehole               |
|           |                                              | and log.                                                |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 361       | ERROR_FLEUR_CALCULATION_FAILED               | Fleur calculation failed.                               | SCF                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 362       | ERROR_DID_NOT_CONVERGE                       | At least one FLEUR calculation did not/could not reach  | Corehole               |
|           |                                              | thedesired convergece Criteria, with the current        |                        |
|           |                                              | parameters.                                             |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 362       | ERROR_DID_NOT_CONVERGE                       | SCF cycle did not lead to convergence.                  | SCF                    |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 380       | ERROR_NOT_SUPPORTED_LATTICE                  | Specified substrate has to be bcc or fcc.               | CreateMagnetic         |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 382       | ERROR_RELAX_FAILED                           | Relaxation calculation failed.                          | CreateMagnetic         |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 383       | ERROR_EOS_FAILED                             | EOS WorkChain failed.                                   | CreateMagnetic         |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 388       | ERROR_TIME_LIMIT_NO_SOLUTION                 | Computational resources are not optimal.                | FleurBase              |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 389       | ERROR_MEMORY_ISSUE_NO_SOLUTION               | Computational resources are not optimal.                | FleurBase              |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 390       | ERROR_NOT_OPTIMAL_RESOURCES                  | Computational resources are not optimal.                | FleurBase              |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 399       | ERROR_SOMETHING_WENT_WRONG                   | FleurCalculation failed and FleurBaseWorkChain has no   | FleurBase              |
|           |                                              | strategy to resolve this                                |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 399       | ERROR_SOMETHING_WENT_WRONG                   | FleurRelaxWorkChain failed and FleurBaseRelaxWorkChain  | RelaxBase              |
|           |                                              | has no strategy to resolve this                         |                        |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 450       | ERROR_SCF_NOLDAU_FAILED                      | Convergence workflow without LDA+U failed.              | OrbControl             |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 451       | ERROR_ORBCONTROL_FAILED                      | Convergence orbcontrol workflow failed.                 | CFCoeff                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
| 452       | ERROR_CFCALC_FAILED                          | CF calculation failed.                                  | CFCoeff                |
+-----------+----------------------------------------------+---------------------------------------------------------+------------------------+
