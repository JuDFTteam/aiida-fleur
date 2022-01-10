.. _orbcontrol_wc:

Fleur orbital occupation control workflow
------------------------------------------

* **Current version**: 0.2.0
* **Class**: :py:class:`~aiida_fleur.workflows.orbcontrol.FleurOrbControlWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.orbcontrol``
* **Workflow type**: Technical
* **Aim**: Find LDA+U groundstate density matrix
* **Computational demand**: Corresponding to several ``FleurSCFWorkChain`` (Can be large depending on number of configurations)
* **Database footprint**: Output node with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes (Can be large depending on number of configurations)
* **File repository footprint**: no addition to the ``CalcJob`` runs

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain
    #or
    WorkflowFactory('fleur.orbcontrol')

Description/Purpose
^^^^^^^^^^^^^^^^^^^

Converges the given system with the ``FleurSCFWorkChain`` with different starting configurations
for the LDA+U density matrix. Each calculation starts with a fixed density matrix which is used for
a configurable number of iterations. After these calculations the density matrix can relax until the
system is converged by the ``FleurSCFWorkChain``

This workflow can be started from either a structure or a already converged calculation **without LDA+U**.
The used configurations can either be provided explicitely or be generated from the given occupations of the
orbital treated with LDA+U.

Input nodes
^^^^^^^^^^^

The table below shows all the possible input nodes of the OrbControl workchain.

+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| name             | type                                                | description                                    | required |
+==================+=====================================================+================================================+==========+
| scf_no_ldau      | namespace                                           | Inputs for SCF calculation before adding LDA+U | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| remote           | :py:class:`~aiida.orm.RemoteData`                   | Remote folder to start the calculations from   | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| fleurinp         | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` | :ref:`FLEUR input<fleurinp_data>`              | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| structure        | :py:class:`~aiida.orm.StructureData`                | Structure to start from without SCF            | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| calc_parameters  | :py:class:`~aiida.orm.Dict`                         | Parameters for Inpgen calculation              | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| scf_with_ldau    | namespace                                           | Inputs for SCF calculations with LDA+U         | yes      |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| fleur            | :py:class:`~aiida.orm.Code`                         | Fleur code                                     | yes      |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| inpgen           | :py:class:`~aiida.orm.Code`                         | Inpgen Code                                    | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| wf_parameters    | :py:class:`~aiida.orm.Dict`                         | Settings of the workchain                      | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
| options          | :py:class:`~aiida.orm.Dict`                         | AiiDA options (computational resources)        | no       |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
|| options_inpgen  || :py:class:`~aiida.orm.Dict`                        || AiiDA options (computational resources)       || no      |
||                 ||                                                    || for the inpgen calculation                    ||         |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
|| settings        || :py:class:`~aiida.orm.Dict`                        || Special :ref:`settings<fleurcode_plugin>`     || no      |
||                 ||                                                    || for Fleur calculation                         ||         |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+
|| settings_inpgen || :py:class:`~aiida.orm.Dict`                        || Special :ref:`settings<fleurcode_plugin>`     || no      |
||                 ||                                                    || for INpgen calculation                        ||         |
+------------------+-----------------------------------------------------+------------------------------------------------+----------+


Only ``fleur`` and ``scf_with_ldau`` input is required. However, it does not mean that it is enough to specify these
only. One *must* keep one of the supported input configurations described in the
:ref:`orbcontrol_wc_layout` section.

Workchain parameters and its defaults
.....................................

.. _FLEUR relaxation: https://www.flapw.de/site/xml-inp/#structure-relaxations-with-fleur


  * ``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
    keys and their defaults are listed below:

    .. literalinclude:: code/orbcontrol_parameters.py

    .. note::

      Only one of ``fixed_occupations`` or ``fixed_configurations`` can be used

  * ``options``: :py:class:`~aiida.orm.Dict` - AiiDA options (computational resources).
    Example:

    .. code-block:: python

         'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
         'max_wallclock_seconds': 6*60*60,
         'queue_name': '',
         'custom_scheduler_commands': '',
         'import_sys_environment': False,
         'environment_variables': {}

Returns nodes
^^^^^^^^^^^^^

The table below shows all the possible output nodes of the SCF workchain.

+----------------------------------+-----------------------------------------------------+-----------------------------------------------------------+
| name                             | type                                                | comment                                                   |
+==================================+=====================================================+===========================================================+
| output_orbcontrol_wc_para        | :py:class:`~aiida.orm.Dict`                         | results of the workchain                                  |
+----------------------------------+-----------------------------------------------------+-----------------------------------------------------------+
| output_orbcontrol_wc_gs_scf      | :py:class:`~aiida.orm.Dict`                         | results of the SCF workchain with the lowest total energy |
+----------------------------------+-----------------------------------------------------+-----------------------------------------------------------+
| output_orbcontrol_wc_gs_fleurinp | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` | FleurinpData corresponding to the calculation             |
|                                  |                                                     | with the lowest total energy                              |
+----------------------------------+-----------------------------------------------------+-----------------------------------------------------------+

More details:

  * ``output_orbcontrol_wc_gs_fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` - A
    :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` that was
    actually used for the groundstate :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain` calculation.
    It differs from the input :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`
    because there are some hard-coded modifications in the SCF workchain
    and the used LDA+U density matrix is included with the file ``n_mmp_mat``.
  * ``output_orbcontrol_wc_para``: :py:class:`~aiida.orm.Dict` -  Main results of the workchain. Contains
    errors, warnings, convergence history and other information. An example:

    .. literalinclude:: code/orbcontrol_wc_outputnode.py

.. _orbcontrol_wc_layout:

Layout
^^^^^^
Similar to other aiida-fleur workchains (e.g. :ref:`SCF workchain layout<scf_wc_layout>`)
input combinations that implicitly define the behaviour of the workchain during
inputs processing. Depending
on the setup of the inputs, one of the four supported scenarios will happen:


1. **fleurinp** + **remote_data** (FLEUR):

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Moreover, initial charge density will be
      copied from the folder of the remote folder. It is important that
      neither **fleurinp** nor **remote_data** correspond to calculations with LDA+U.

2. **fleurinp**:

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Should not represent an LDA+U input.

3. **remote_data** (FLEUR):

      inp.xml file and initial
      charge density will be copied from the remote folder. Should not represent a LDA+U calculation

4. **structure** + **calc_parameters**(optional) + **inpgen**:
  
      The initial structure is used to generate a `FleurinpData` object via the input generator.
      This is used to start the LDA+U calculations without a SCF workchain. directly starting with
      the fixed LDA+U density matrices

5. **scf_no_ldau**:

      A ``FleurSCFWorkChain`` is started with the input in the **scf_no_ldau**
      namespace and the output is used as a starting point for the LDA+U calculations

.. warning::

  One *must* keep one of the supported input configurations. In other case the workchain will
  stop throwing exit code 230.

The general layout does not depend on the scenario.


Error handling
^^^^^^^^^^^^^^
In case of failure the OrbControl WorkChain should throw one of the :ref:`exit codes<exit_codes>`:

+-----------+----------------------------------------------+
| Exit Code | Reason                                       |
+===========+==============================================+
| 230       | Invalid workchain parameters                 |
+-----------+----------------------------------------------+
| 231       | Invalid input configuration                  |
+-----------+----------------------------------------------+
|| 233      || Invalid code node specified, check          |
||          || fleur code nodes                            |
+-----------+----------------------------------------------+
| 235       | Input file modification failed               |
+-----------+----------------------------------------------+
| 236       | Input file was corrupted after modifications |
+-----------+----------------------------------------------+
|| 342      || Some of the LDA+U calculations failed       |
||          || This is expected for many situations        |
+-----------+----------------------------------------------+
| 343       | All of the LDA+U calculations failed         |
+-----------+----------------------------------------------+
| 360       | The inpgen calculation failed                |
+-----------+----------------------------------------------+
| 450       | SCF calculation without LDA+U failed         |
+-----------+----------------------------------------------+

If your workchain crashes and stops in *Excepted* state, please open a new issue on the Github page
and describe the details of the failure.

Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    plot_fleur(50816)

  .. figure:: images/plot_fleur_orbcontrol.pdf
    :width: 60 %
    :align: center
