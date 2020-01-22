.. _exit_codes:

Exit codes
**********

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
