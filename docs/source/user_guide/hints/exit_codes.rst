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


The list of all exit codes implemented in AiiDA-FLEUR:

+-----------+---------------------------------------------------------+------------------------+
| Exit code | Exit message                                            | Thrown by              |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | CreateMagnetic         |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | DMI                    |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | EOS                    |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | MAE                    |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | MAE Conv               |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | Relax                  |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | SCF                    |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | SSDisp                 |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | SSDisp Conv            |
+-----------+---------------------------------------------------------+------------------------+
| 230       | Invalid workchain parameters                            | BandDos                |
+-----------+---------------------------------------------------------+------------------------+
| 231       | Invalid input configuration                             | CreateMagnetic         |
+-----------+---------------------------------------------------------+------------------------+
| 231       | Invalid input configuration                             | DMI                    |
+-----------+---------------------------------------------------------+------------------------+
| 231       | Invalid input configuration                             | MAE                    |
+-----------+---------------------------------------------------------+------------------------+
| 231       | Invalid input configuration                             | SCF                    |
+-----------+---------------------------------------------------------+------------------------+
| 231       | Invalid input configuration                             | SSDisp                 |
+-----------+---------------------------------------------------------+------------------------+
| 231       | Invalid input configuration                             | BandDos                |
+-----------+---------------------------------------------------------+------------------------+
| 233       | Input codes do not correspond to                        | DMI                    |
|           | fleur or inpgen codes respectively.                     |                        |
+-----------+---------------------------------------------------------+------------------------+
| 233       | Input codes do not correspond to                        | MAE                    |
|           | fleur or inpgen codes respectively.                     |                        |
+-----------+---------------------------------------------------------+------------------------+
| 233       | Input codes do not correspond to                        | SSDisp                 |
|           | fleur or inpgen codes respectively.                     |                        |
+-----------+---------------------------------------------------------+------------------------+
| 233       | Input codes do not correspond to                        | BandDos                |
|           | fleur or inpgen codes respectively.                     |                        |
+-----------+---------------------------------------------------------+------------------------+
| 235       | Input file modification failed.                         | DMI                    |
+-----------+---------------------------------------------------------+------------------------+
| 235       | Input file modification failed.                         | MAE                    |
+-----------+---------------------------------------------------------+------------------------+
| 235       | Input file modification failed                          | SCF                    |
+-----------+---------------------------------------------------------+------------------------+
| 235       | Input file modification failed.                         | SSDisp                 |
+-----------+---------------------------------------------------------+------------------------+
| 235       | Input file modification failed.                         | BandDos                |
+-----------+---------------------------------------------------------+------------------------+
| 236       | Input file was corrupted after modifications            | DMI                    |
+-----------+---------------------------------------------------------+------------------------+
| 236       | Input file was corrupted after modifications            | MAE                    |
+-----------+---------------------------------------------------------+------------------------+
| 236       | Input file was corrupted after modifications            | SCF                    |
+-----------+---------------------------------------------------------+------------------------+
| 236       | Input file was corrupted after modifications            | SSDisp                 |
+-----------+---------------------------------------------------------+------------------------+
| 236       | Input file was corrupted after modifications            | BandDos                |
+-----------+---------------------------------------------------------+------------------------+
| 300       | No retrieved folder found                               | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 300       | No retrieved folder found                               | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 300       | No retrieved folder found                               | FleurinpgenCalculation |
+-----------+---------------------------------------------------------+------------------------+
| 300       | No retrieved folder found                               | FleurinpgenCalculation |
+-----------+---------------------------------------------------------+------------------------+
| 301       | One of the output files can not be opened               | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 301       | One of the output files can not be opened               | FleurinpgenCalculation |
+-----------+---------------------------------------------------------+------------------------+
| 302       | FLEUR calculation failed for unknown reason             | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 303       | XML output file was not found                           | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 304       | Parsing of XML output file failed                       | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 305       | Parsing of relax XML output file failed                 | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 306       | XML input file was not found                            | FleurinpgenCalculation |
+-----------+---------------------------------------------------------+------------------------+
| 310       | FLEUR calculation failed due to memory issue            | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 311       | FLEUR calculation failed because atoms                  | FleurBase              |
|           | spilled to the vacuum                                   |                        |
+-----------+---------------------------------------------------------+------------------------+
| 311       | FLEUR calculation failed because atoms                  | FleurCalculation       |
|           | spilled to the vacuum                                   |                        |
+-----------+---------------------------------------------------------+------------------------+
| 311       | FLEUR calculation failed because atoms                  | Relax                  |
|           | spilled to the vacuum                                   |                        |
+-----------+---------------------------------------------------------+------------------------+
| 312       | FLEUR calculation failed due to MT overlap              | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 313       | Overlapping MT-spheres during relaxation                | FleurBase              |
+-----------+---------------------------------------------------------+------------------------+
| 313       | Overlapping MT-spheres during relaxation                | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 313       | Overlapping MT-spheres during relaxation                | Relax                  |
+-----------+---------------------------------------------------------+------------------------+
| 314       | Problem with cdn is suspected                           | Relax                  |
+-----------+---------------------------------------------------------+------------------------+
| 316       | Calculation failed due to time limits.                  | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 318       | Calculation failed due to a missing dependency          | FleurCalculation       |
+-----------+---------------------------------------------------------+------------------------+
| 334       | Reference calculation failed.                           | DMI                    |
+-----------+---------------------------------------------------------+------------------------+
| 334       | Reference calculation failed.                           | MAE                    |
+-----------+---------------------------------------------------------+------------------------+
| 334       | Reference calculation failed.                           | SSDisp                 |
+-----------+---------------------------------------------------------+------------------------+
| 334       | SCF calculation failed.                                 | BandDos                |
+-----------+---------------------------------------------------------+------------------------+
| 335       | Found no reference calculation remote repository.       | DMI                    |
+-----------+---------------------------------------------------------+------------------------+
| 335       | Found no reference calculation remote repository.       | MAE                    |
+-----------+---------------------------------------------------------+------------------------+
| 335       | Found no reference calculation remote repository.       | SSDisp                 |
+-----------+---------------------------------------------------------+------------------------+
| 335       | Found no SCF calculation remote repository.             | BandDos                |
+-----------+---------------------------------------------------------+------------------------+
| 336       | Force theorem calculation failed.                       | DMI                    |
+-----------+---------------------------------------------------------+------------------------+
| 336       | Force theorem calculation failed.                       | MAE                    |
+-----------+---------------------------------------------------------+------------------------+
| 336       | Force theorem calculation failed.                       | SSDisp                 |
+-----------+---------------------------------------------------------+------------------------+
| 340       | Convergence SSDisp calculation failed                   | SSDisp conv            |
|           | for all q-vectors                                       |                        |
+-----------+---------------------------------------------------------+------------------------+
| 341       | Convergence SSDisp calculation failed                   | SSDisp conv            |
|           | for some q-vectors                                      |                        |
+-----------+---------------------------------------------------------+------------------------+
| 343       | Convergence MAE calculation failed for all SQAs         | MAE conv               |
+-----------+---------------------------------------------------------+------------------------+
| 344       | Convergence MAE calculation failed for some SQAs        | MAE conv               |
+-----------+---------------------------------------------------------+------------------------+
| 350       | The workchain execution did not lead to                 | Relax                  |
|           | relaxation criterion. Thrown in the very                |                        |
|           | end of the workchain.                                   |                        |
+-----------+---------------------------------------------------------+------------------------+
| 351       | SCF Workchains failed for some reason.                  | Relax                  |
+-----------+---------------------------------------------------------+------------------------+
| 352       | Found no relaxed structure info in the output of SCF    | Relax                  |
+-----------+---------------------------------------------------------+------------------------+
| 353       | Found no SCF output                                     | Relax                  |
+-----------+---------------------------------------------------------+------------------------+
| 354       | Force is small, switch to BFGS                          | Relax                  |
+-----------+---------------------------------------------------------+------------------------+
| 360       | Inpgen calculation failed                               | SCF                    |
+-----------+---------------------------------------------------------+------------------------+
| 360       | Inpgen calculation failed                               | OrbControl             |  
+-----------+---------------------------------------------------------+------------------------+
| 361       | Fleur calculation failed                                | SCF                    |
+-----------+---------------------------------------------------------+------------------------+
| 380       | Specified substrate is not bcc or fcc,                  | CreateMagnetic         |
|           | only them are supported                                 |                        |
+-----------+---------------------------------------------------------+------------------------+
| 382       | Relaxation calculation failed.                          | CreateMagnetic         |
+-----------+---------------------------------------------------------+------------------------+
| 383       | EOS WorkChain failed.                                   | CreateMagnetic         |
+-----------+---------------------------------------------------------+------------------------+
| 388       | Fleur Calculation failed due to time limits             | FleurBase              |
|           | and it cannot be resolved (e.g because of no cdn file)  |                        |
+-----------+---------------------------------------------------------+------------------------+
| 389       | FLEUR calculation failed due to memory issue            | FleurBase              |
|           | and it can not be solved for this scheduler             |                        |
+-----------+---------------------------------------------------------+------------------------+
| 390       | check_kpts() suggests less than 60% of node load        | FleurBase              |
+-----------+---------------------------------------------------------+------------------------+
| 399       | FleurCalculation failed and FleurBaseWorkChain          | FleurBase              |
|           | has no strategy to resolve this                         |                        |
+-----------+---------------------------------------------------------+------------------------+
| 399       | FleurRelaxWorkChain failed and                          | Relax Base             |
|           | FleurBaseRelaxWorkChain has no strategy to resolve this |                        |
+-----------+---------------------------------------------------------+------------------------+
