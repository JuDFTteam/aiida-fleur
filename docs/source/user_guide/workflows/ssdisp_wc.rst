.. _ssdisp_wc:

Fleur Spin-Spiral Dispersion workchain
--------------------------------------

* **Current version**: 0.1.0
* **Class**: :py:class:`~aiida_fleur.workflows.ssdisp.FleurSSDispWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.ssdisp``
* **Workflow type**: Scientific workchain, force-theorem subgroup

.. contents::
    :depth: 2

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.ssdisp import FleurSSDispWorkChain
    #or
    WorkflowFactory('fleur.ssdisp')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
This workchain calculates spin spiral energy  dispersion over a given set of q-points.
Resulting energies do not contain terms, corresponding to DMI energies. To take into account DMI,
see the :ref:`dmi_wc` documentation.

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
:ref:`layout_ssdisp` section.

Workchain parameters and its defaults
.....................................

.. _FLEUR relaxation: https://www.flapw.de/site/xml-inp/#structure-relaxations-with-fleur

``wf_parameters``
,,,,,,,,,,,,,,,,,

``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
keys and their defaults are listed below:

.. literalinclude:: code/ssdisp_parameters.py

Workchain parameters contain a set of parameters needed by the SCF workchain.
There are also SSDisp-specific parameters such as ``beta``, ``alpha-mix``, ``prop_dir``,
``q_vectors``, ``ref_qss`` and ``input_converged``.

``beta`` is a python dictionary containing a key: value pairs. Each pair sets ``beta`` parameter
in an inp.xml file. Key string corresponds to the atom label, if key equals `all` then all atoms
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

``prop_dir`` is used only if inpgen must be run (structure node given in the inputs). This
value is passed to ``calc_parameters['qss']`` and written into the input for inpgen. It shows
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

        "energies": [
            0.0,
            0.00044082445345511,
        ],
        "energy_units": "eV",
        "errors": [],
        "info": [],
        "initial_structure": "a75459e5-f83e-4aff-a25d-595d938cb841",
        "is_it_force_theorem": true,
        "q_vectors": [
            [
                0.0,
                0.0,
                0.0
            ],
            [
                0.125,
                0.125,
                0.0
            ],
        ],
        "warnings": [],
        "workflow_name": "FleurSSDispWorkChain",
        "workflow_version": "0.1.0"

    Resulting Spin Spiral energies are sorted according to theirs q-vectors
    i.e. ``energies[N]`` corresponds to ``q_vectors[N]``.

.. _layout_ssdisp:

Supported input configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SSDisp workchain has several
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
        #. prop_dir
        #. q_vectors
        #. inpxml_changes

      The other are ignored.

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

.. warning::

  One *must* keep one of the supported input configurations. In other case the workchain will
  stop throwing non-zero exit status or more dangerously, will make unexpected actions.


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

  .. literalinclude:: code/ssdisp_wc_submission.py
