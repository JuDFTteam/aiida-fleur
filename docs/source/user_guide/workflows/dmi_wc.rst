.. _dmi_wc:

Fleur Dzyaloshinskii–Moriya Interaction energy workchain
--------------------------------------------------------

* **Current version**: 0.1.0
* **Class**: :py:class:`~aiida_fleur.workflows.dmi.FleurDMIWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.dmi``
* **Workflow type**: Scientific workchain, force theorem sub-group

.. contents::
    :depth: 2

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.dmi import FleurDMIWorkChain
    #or
    WorkflowFactory('fleur.dmi')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
This workchain calculates Dzyaloshinskii–Moriya Interaction energy over a given set of q-points.

In this workchain the force-theorem is employed which means the workchain converges
a reference charge density first
then it submits a single FleurCalculation with a ``<forceTheorem>`` tag. However, it is possible
to specify inputs to use external pre-converged charge density and use is as a reference.

Input nodes
^^^^^^^^^^^

+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| name            | type                                               | description                             | required |
+=================+====================================================+=========================================+==========+
| fleur           | :py:class:`~aiida.orm.Code`                        | Fleur code                              | yes      |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| inpgen          | :py:class:`~aiida.orm.Code`                        | Inpgen code                             | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| wf_parameters   | :py:class:`~aiida.orm.Dict`                        | Settings of the workchain               | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| structure       | :py:class:`~aiida.orm.StructureData`               | Structure data node                     | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| calc_parameters | :py:class:`~aiida.orm.Dict`                        | inpgen :ref:`parameters<scf_wc_layout>` | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleurinp        | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`| :ref:`FLEUR input<fleurinp_data>`       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| remote_data     | :py:class:`~aiida.orm.RemoteData`                  | Remote folder of another calculation    | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| options         | :py:class:`~aiida.orm.Dict`                        | AiiDA options (computational resources) | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| settings        | :py:class:`~aiida.orm.Dict`                        | Special :ref:`settings<fleurinp_data>`  |          |
|                 |                                                    | for Fleur calculation                   | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+

Only ``fleur`` input is required. However, it does not mean that it is enough to specify ``fleur``
only. One *must* keep one of the supported input configurations described in the
:ref:`layout_dmi` section.

Workchain parameters and its defaults
.....................................

.. _FLEUR relaxation: https://www.flapw.de/site/xml-inp/#structure-relaxations-with-fleur

``wf_parameters``
,,,,,,,,,,,,,,,,,

``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
keys and their defaults are listed below:

.. literalinclude:: code/ssdisp_parameters.py

Workchain parameters contain a set of parameters needed by the SCF workchain.
There are also DMI-specific parameters such as ``beta``, ``alpha-mix``, ``prop_dir``,
``q_vectors``, ``ref_qss``, ``sqas_theta``, ``sqas_phi``, ``soc_off`` and ``input_converged``.

``beta`` is a python dictionary containing a key: value pairs. Each pair sets ``beta`` parameter
in an inp.xml file. Key string corresponds to the atom label, if key equals to 'all' then all atoms
will be changed. For example,

.. code-block:: python

    'beta' : {'222' : 1.57079}

changes

.. code-block:: html

      <atomGroup species="Fe-1">
        <filmPos label="                 222">.0000000000 .0000000000 -11.4075100502</filmPos>
        <force calculate="T" relaxXYZ="TTT"/>
        <nocoParams l_relax="F" alpha=".00000000" beta="0.00000" b_cons_x=".00000000" b_cons_y=".00000000"/>
      </atomGroup>

to:

.. code-block:: html

      <atomGroup species="Fe-1">
        <filmPos label="                 222">.0000000000 .0000000000 -11.4075100502</filmPos>
        <force calculate="T" relaxXYZ="TTT"/>
        <nocoParams l_relax="F" alpha=".00000000" beta="1.57079" b_cons_x=".00000000" b_cons_y=".00000000"/>
      </atomGroup>

.. note::

      More correctly, ``beta`` set a beta parameter for not an atom, but for a whole atomGroup.
      It might be the case when beta is set for an atom that is not intended to change it's beta
      value. To avoid this, you need to specify species and atomGroups differently, see the LINK.

``soc_off`` is a python list containing atoms labels. SOC is switched off for species, corresponding
to the atom with a given label.

.. note::

    It can be that the spice correspond to several atoms and ``soc_off`` switches off SOC for atoms
    that was not intended to change. You must be careful with this.

An example of ``soc_off`` work:

.. code-block:: python

    'soc_off': ['458']

changes

.. code-block:: html

      <species name="Ir-2" element="Ir" atomicNumber="77" coreStates="17" magMom=".00000000" flipSpin="T">
        <mtSphere radius="2.52000000" gridPoints="747" logIncrement=".01800000"/>
        <atomicCutoffs lmax="8" lnonsphr="6"/>
        <energyParameters s="6" p="6" d="5" f="5"/>
        <prodBasis lcutm="4" lcutwf="8" select="4 0 4 2"/>
        <lo type="SCLO" l="1" n="5" eDeriv="0"/>
      </species>
      -----
      <atomGroup species="Ir-2">
        <filmPos label="                 458">1.000/4.000 1.000/2.000 11.4074000502</filmPos>
        <force calculate="T" relaxXYZ="TTT"/>
        <nocoParams l_relax="F" alpha=".00000000" beta=".00000000" b_cons_x=".00000000" b_cons_y=".00000000"/>
      </atomGroup>

to:

.. code-block:: html

      <species name="Ir-2" element="Ir" atomicNumber="77" coreStates="17" magMom=".00000000" flipSpin="T">
        <mtSphere radius="2.52000000" gridPoints="747" logIncrement=".01800000"/>
        <atomicCutoffs lmax="8" lnonsphr="6"/>
        <energyParameters s="6" p="6" d="5" f="5"/>
        <prodBasis lcutm="4" lcutwf="8" select="4 0 4 2"/>
        <special socscale="0.0"/>
        <lo type="SCLO" l="1" n="5" eDeriv="0"/>
      </species>

As you can see, I was careful about "Ir-2" specie  and it contained a single atom with a
label 458.

.. _Fleur forceTheorem documentation: https://www.flapw.de/site/xml-advanced/#dzyaloshinskii-moriya-interaction

``sqas_theta`` and ``sqas_phi`` are python lists that set SOC theta and phi values. For detailed
explanation see `Fleur forceTheorem documentation`_.

``prop_dir`` is used only if inpgen must be run (structure node given in the inputs). This
value is passed to `calc_parameters['qss']` and written into the input for inpgen. Thus it shows
the intention of a user on what kind of q-mesh he/she wants to use to properly set up
symmetry operations in the reference calculation.

``input_converged`` is used only if a ``remote_date`` node is given in the input. Is has to be set
True if there is no need to converge a given charge density and it can be used directly for the
force-theorem step. If it is set to False, input charge density will be submitted into scf
workchain before the force-theorem step to achieve the convergence.

``options``
,,,,,,,,,,,

``options``: :py:class:`~aiida.orm.Dict` - AiiDA options (computational resources).
Example:

.. code-block:: python

      'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
      'max_wallclock_seconds': 6*60*60,
      'queue_name': '',
      'custom_scheduler_commands': '',
      'import_sys_environment': False,
      'environment_variables': {}


Output nodes
^^^^^^^^^^^^^

  * ``out``: :py:class:`~aiida.orm.Dict` -  Information of
    workflow results like success, last result node, list with convergence behavior

    .. code-block:: python

        "angles": 3,
        "energies": [
            0.0
        ],
        "energy_units": "eV",
        "errors": [],
        "info": [],
        "initial_structure": "35e5058d-161c-4cf9-801e-4eca99e7d7be",
        "phi": [
            3.1415927,
        ],
        "q_vectors": [
            [
                0.0,
                0.0,
                0.0
            ],
        ],
        "theta": [
            0.0,
        ],
        "warnings": [],
        "workflow_name": "FleurDMIWorkChain",
        "workflow_version": "0.1.0"

    Resulting DMI energies are sorted according to theirs q-vector, theta and phi values
    i.e. ``energies[N]`` corresponds to ``q_vectors[N]``, ``phi[N]`` and ``theta[N]``.

.. _layout_dmi:

Supported input configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ВЬШ workchain has several
input combinations that implicitly define the workchain layout. Depending
on the setup of the inputs, one of four supported scenarios will happen:

1. **fleurinp**:

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Submits SCF workchain to obtain the reference charge density, then
      makes a force-theorem FLEUR calculation.

      Workchain parameters that are used:

        #. SCF-related parameters
        #. beta
        #. alpha_mix
        #. sqas_theta
        #. sqas_phi
        #. soc_off
        #. prop_dir
        #. q_vectors
        #. inpxml_changes

      The others are ignored.

2. **fleurinp** + **parent_folder** (FLEUR):

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Moreover, initial charge density will be
      copied from the folder of the parent calculation. If ``input_converged`` set to False,
      first submits a SCF workchain to converge given charge density further; directly submits
      a force-theorem calculation otherwise.


3. **parent_folder** (FLEUR):

      inp.xml file and initial
      charge density will be copied from the folder of the parent FLEUR calculation.
      If ``input_converged`` set to False, first
      submits a SCF workchain to converge given charge density further; directly submits
      a force-theorem calculation otherwise.

4. **structure**:

      Submits inpgen calculation to generate a new **fleurinp** using a given structure which
      is followed by the SCF workchain to obtain the reference charge density. Submits a
      force-theorem FLEUR calculation after.



Error handling
^^^^^^^^^^^^^^
A list of implemented exit codes:

+------+------------------------------------------------------------------------------------------+
| Code | Meaning                                                                                  |
+======+==========================================================================================+
| 230  | Input nodes do not correspond to any valid input configuration.                          |
+------+------------------------------------------------------------------------------------------+
| 231  | Input codes do not correspond to fleur or inpgen codes respectively.                     |
+------+------------------------------------------------------------------------------------------+
| 232  | Input file modification failed.                                                          |
+------+------------------------------------------------------------------------------------------+
| 233  | Input file is corrupted after user's modifications.                                      |
+------+------------------------------------------------------------------------------------------+
| 334  | Reference calculation failed.                                                            |
+------+------------------------------------------------------------------------------------------+
| 335  | Found no reference calculation remote repository.                                        |
+------+------------------------------------------------------------------------------------------+
| 336  | Force theorem calculation failed.                                                        |
+------+------------------------------------------------------------------------------------------+

Example usage
^^^^^^^^^^^^^
Still has to be documented
