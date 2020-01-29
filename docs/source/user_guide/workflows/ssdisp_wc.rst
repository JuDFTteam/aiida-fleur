.. _ssdisp_wc:

Fleur Spin-Spiral Dispersion workchain
--------------------------------------

* **Current version**: 0.2.0
* **Class**: :py:class:`~aiida_fleur.workflows.ssdisp.FleurSSDispWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.ssdisp``
* **Workflow type**: Scientific workchain, force-theorem subgroup

.. contents::
    :depth: 2

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.ssdisp_conv import FleurSSDispWorkChain
    #or
    WorkflowFactory('fleur.ssdisp')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
This workchain calculates spin spiral energy  dispersion over a given set of q-points.
Resulting energies do not contain terms, corresponding to DMI energies. To take into account DMI,
see the :ref:`dmi_wc` documentation.

In this workchain the force-theorem is employed which means the workchain converges
a reference charge density first
and then submits a single FleurCalculation with a ``<forceTheorem>`` tag. However, it is possible
to specify inputs to use external pre-converged charge density to use it as a reference.

The task of the workchain us to calculate the energy difference between two or several structures
having a different magnetisation profile:

.. image:: images/ssdisp_energies.png
    :width: 60%
    :align: center

To do this, the workchain employs the force theorem approach:

.. image:: images/ssdisp_force.png
    :width: 110%
    :align: center

As it was mentioned, it is not always necessary to start with a structure. Setting up input
parameters correctly (see :ref:`layout_ssdisp`) one can start from a given FleuinpData, inp.xml
or converged/not-fully-converged reference charge density.

.. _exposed: https://aiida.readthedocs.io/projects/aiida-core/en/latest/working/workflows.html#working-workchains-expose-inputs-outputs

Input nodes
^^^^^^^^^^^

The FleurSSDispWorkChain employs
`exposed`_ feature of the AiiDA, thus inputs for the nested
:ref:`SCF<scf_wc>` workchain should be passed in the namespace
``scf``.

+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| name            | type                                               | description                             | required |
+=================+====================================================+=========================================+==========+
| scf             | namespace                                          | inputs for nested SCF WorkChain         | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleur           | :py:class:`~aiida.orm.Code`                        | Fleur code                              | yes      |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| wf_parameters   | :py:class:`~aiida.orm.Dict`                        | Settings of the workchain               | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleurinp        | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`| :ref:`FLEUR input<fleurinp_data>`       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| remote          | :py:class:`~aiida.orm.RemoteData`                  | Remote folder of another calculation    | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| options         | :py:class:`~aiida.orm.Dict`                        | AiiDA options (computational resources) | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+

.. | settings        | :py:class:`~aiida.orm.Dict`                        | Special :ref:`settings<fleurinp_data>`  |          |
.. |                 |                                                    | for Fleur calculation                   | no       |
.. +-----------------+----------------------------------------------------+-----------------------------------------+----------+

Only **fleur** input is required. However, it does not mean that it is enough to specify **fleur**
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

**beta** is a python dictionary containing a ``key: value`` pairs. Each pair sets **beta** parameter
in an inp.xml file. ``key`` specifies the atom label to change, ``key`` equal to `'all'` sets all
atoms groups. For example,

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

      **beta** actually sets a beta parameter for a whole atomGroup.
      It can be that the atomGroup correspond to several atoms and **beta** switches sets beta
      for atoms
      that was not intended to change. You must be careful and make sure that several atoms do not
      correspond to a given specie.

**prop_dir** is used only to set up a spin spiral propagation direction to
``calc_parameters['qss']`` which will be passed to SCF workchain and inpgen. It can be used
to properly set up symmetry operations in the reference calculation.

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
input combinations that implicitly define the workchain layout. Only **scf**, **fleurinp** and
**remote** nodes control the behaviour, other input nodes are truly optional.
Depending on the setup of the given inputs, one of three supported scenarios will happen:

1. **scf**:

      SCF workchain will be submitted to converge the reference charge density which will
      be followed be the force theorem calculation. Depending on the inputs given in the SCF
      namespace, SCF will start from the structure or FleurinpData or will continue
      converging from the given remote_data (see details in :ref:`SCF WorkChain<scf_wc>`).

2. **remote**:

      Files which belong to the **remote** will be used for the direct submission of the force
      theorem calculation. ``inp.xml`` file will be converted to FleurinpData and charge density
      will be used as a reference charge density.

3. **remote** + **fleurinp**:

      Charge density which belongs to **remote** will be used as a reference charge density, however
      ``inp.xml`` from the **remote** will be ignored. Instead, the given **fleurinp** will be used.
      The aforementioned input files will be used for direct submission of the force theorem
      calculation.

Other combinations of the input nodes **scf**, **fleurinp** and **remote** are forbidden.

.. warning::

  One *must* follow one of the supported input configurations. To protect a user from the
  workchain misbehaviour, an error will be thrown if one specifies e.g. both **scf** and **remote**
  inputs because in this case the intention of the user is not clear either he/she wants to
  converge a new charge density or use the given one.


Error handling
^^^^^^^^^^^^^^
A list of implemented :ref:`exit codes<exit_codes>`:

+------+------------------------------------------------------------------------------------------+
| Code | Meaning                                                                                  |
+======+==========================================================================================+
| 230  | Invalid workchain parameters                                                             |
+------+------------------------------------------------------------------------------------------+
| 231  | Invalid input configuration                                                              |
+------+------------------------------------------------------------------------------------------+
| 233  | Input codes do not correspond to fleur or inpgen codes respectively.                     |
+------+------------------------------------------------------------------------------------------+
| 235  | Input file modification failed.                                                          |
+------+------------------------------------------------------------------------------------------+
| 236  | Input file was corrupted after modifications                                             |
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
