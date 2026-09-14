Fleur input generator plug-in
+++++++++++++++++++++++++++++


Fleurinputgen Calculation
-------------------------
.. automodule:: aiida_fleur.calculation.fleurinputgen
   :members:


Fleurinputgen Parser
--------------------
.. automodule:: aiida_fleur.parsers.fleur_inputgen
   :members:


Fleur-code plugin
+++++++++++++++++

Fleur Calculation
-----------------
.. automodule:: aiida_fleur.calculation.fleur
   :members:

   
Fleur Parser
------------
.. automodule:: aiida_fleur.parsers.fleur
   :members:

Fleur input Data structure
++++++++++++++++++++++++++


Fleur input Data structure
--------------------------
.. automodule:: aiida_fleur.data.fleurinp
   :members:
   :special-members: __init__

Fleurinp modifier
-----------------

.. automodule:: aiida_fleur.data.fleurinpmodifier
   :members:
   :inherited-members:
   :exclude-members: modify_xmlfile

.. _code_wc:

Workflows/Workchains
++++++++++++++++++++

Base: Fleur-Base WorkChain
----------------------------

.. automodule:: aiida_fleur.workflows.base_fleur
   :members:

BaseRelax: Fleur-Base-Relax WorkChain
-------------------------------------

.. automodule:: aiida_fleur.workflows.base_relax
   :members:

SCF: Fleur-Scf WorkChain
-------------------------

.. automodule:: aiida_fleur.workflows.scf
   :members:

BandDos: Bandstructure WorkChain
--------------------------------

.. automodule:: aiida_fleur.workflows.banddos
   :members:

EOS: Calculate a lattice constant
---------------------------------

.. automodule:: aiida_fleur.workflows.eos
   :members:

Relax: Relaxation of a Cystalstructure WorkChain
-------------------------------------------------

.. automodule:: aiida_fleur.workflows.relax
   :members:

initial_cls: Caluclation of inital corelevel shifts
---------------------------------------------------

.. automodule:: aiida_fleur.workflows.initial_cls
   :members:

corehole: Performance of coreholes calculations
-----------------------------------------------

.. automodule:: aiida_fleur.workflows.corehole
   :members:

MAE: Force-theorem calculation of magnetic anisotropy energies
----------------------------------------------------------------

.. automodule:: aiida_fleur.workflows.mae
   :members:

MAE Conv: Self-consistent calculation of magnetic anisotropy energies
----------------------------------------------------------------------------

.. automodule:: aiida_fleur.workflows.mae_conv
   :members:

SSDisp: Force-theorem calculation of spin spiral dispersion
----------------------------------------------------------------

.. automodule:: aiida_fleur.workflows.ssdisp
   :members:

SSDisp Conv: Self-consistent calculation of spin spiral dispersion
-----------------------------------------------------------------------

.. automodule:: aiida_fleur.workflows.ssdisp_conv
   :members:

DMI: Force-theorem calculation of Dzjaloshinskii-Moriya interaction energy dispersion
----------------------------------------------------------------------------------------

.. automodule:: aiida_fleur.workflows.dmi
   :members:

OrbControl: Self-consistent calculation of groundstate density matrix with LDA+U
----------------------------------------------------------------------------------------

.. automodule:: aiida_fleur.workflows.orbcontrol
   :members:

CFCoeff: Calculation of 4f crystal field coefficients
------------------------------------------------------

.. automodule:: aiida_fleur.workflows.cfcoeff
   :members:

Jij: Calculation of the full Jij exchange tensor
-------------------------------------------------

.. automodule:: aiida_fleur.workflows.jij
   :members:

RelaxTorque: Spin structure optimization
-----------------------------------------

.. automodule:: aiida_fleur.workflows.relax_torque
   :members:

Strain: Calculation of the deformation potential
-------------------------------------------------

.. automodule:: aiida_fleur.workflows.strain
   :members:

CutoffConv: Kmax, k-point and smearing convergence
---------------------------------------------------

.. automodule:: aiida_fleur.workflows.cutoff_conv
   :members:

FSM: Fixed spin moment calculations
------------------------------------

.. automodule:: aiida_fleur.workflows.fsm
   :members:

CreateMagnetic: Create a relaxed magnetic film
-----------------------------------------------

.. automodule:: aiida_fleur.workflows.create_magnetic_film
   :members:



Commandline interface (CLI)
+++++++++++++++++++++++++++
.. _aiidafleur_cmdline:

.. click:: aiida_fleur.cmdline:cmd_root
    :prog: aiida-fleur
    :show-nested:
