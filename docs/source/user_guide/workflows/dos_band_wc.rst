.. _dos_band_wc:

Fleur dos/band workflow
------------------------

These are two seperate workflows which are pretty similar so we treat them here together

* **Class**: :py:class:`~aiida_fleur.workflows.banddos.FleurBandDosWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.banddos``
* **Workflow type**:  Workflow (lvl 1)
* **Aim**: Calculate a density of states. Calculate a band structure.
* **Computational demand**: 1 ``Fleur Job calculation`` + 1 (optional) ``Fleur SCF workflow``
* **Database footprint**: Outputnode with information, full provenance, ``~ 10`` nodes (more if SCF workflow is included)
* **File repository footprint**: The ``JobCalculation`` run, plus the DOS or Bandstructure files

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.banddos import FleurBandDosWorkChain
    #or
    WorkflowFactory('fleur.banddos')

Description/Purpose
^^^^^^^^^^^^^^^^^^^

  Calculates an electronic band structure on top of a given Fleur calculation (converged or not). It can be started from the crystal structure utilizing the FleurSCFWorkchain as a subworkchain

  This workflow prepares/changes the Fleur input with respect to the kpoint set and bandstructure/DOS related parameters and manages one Fleur calculation.

Input nodes:
^^^^^^^^^^^^
.. _exposed: https://aiida.readthedocs.io/projects/aiida-core/en/latest/working/workflows.html#working-workchains-expose-inputs-outputs

The FleurBandDosWorkChain employs
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
| kpoints         | :py:class:`~aiida.orm.KpointsData`                 | Kpoint-set to use                       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| options         | :py:class:`~aiida.orm.Dict`                        | AiiDA options (computational resources) | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+

Only the **fleur** input is required. However, it does not mean that it is enough to specify **fleur**
only. One *must* keep one of the supported input configurations described in the
:ref:`layout_banddos` section.

Returns nodes
^^^^^^^^^^^^^

The table below shows all the possible output nodes of the BandDos workchain.

+-------------------------+------------------------------------------------------+------------------------------------------------------+
| name                    |type                                                  |comment                                               |
+=========================+======================================================+======================================================+
| output_banddos_wc_para  |:py:class:`~aiida.orm.Dict`                           |results of the workchain                              |
+-------------------------+------------------------------------------------------+------------------------------------------------------+
| last_calc_retrieved     |:py:class:`~aiida.orm.FolderData`                     |Link to last FleurCalculation retrieved files         |
+-------------------------+------------------------------------------------------+------------------------------------------------------+

Workchain parameters and its defaults
.....................................

``wf_parameters``
,,,,,,,,,,,,,,,,,

``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
keys and their defaults are listed below:

.. literalinclude:: code/banddos_parameters.py

**mode** is a string (either ``band``(default) or ``dos``). Determines, whether a bandstructure or density of states calculation is performed. This sets the ``band`` and ``dos`` switches in the ``output`` section of the input file accordingly.

**kpath** is only used if ``mode='band'`` to determine the kpath to use. There are 5 different options here:

* ``auto`` Will use the default bandpath in fleur for both Max4 or Max5. If ``klistname`` is given the corresponding kpoint path is used for Max5 version or later
* A `dictionary` specifying the special points and their coordinates. Only available for versions before Max5. Will generate a kpath with ``kpoints_number`` points
* ``seek`` will use :py:func:`~aiida.tools.data.array.kpoints.get_explicit_kpoints_path()` to generate a kpath with the given ``kpoints_distance``.

  .. warning::
    This functionality only works for standardized primitive unit cells.
* ``skip`` nothing is done
* all **other strings** are used to generate a k-path using :py:func:`~ase.dft.kpoints.bandpath()` for example ``GMKGALHA``. This option supports both ``kpoints_number`` and ``kpoints_distance`` for specifying the number of points


**kpoints_number** integer specifying the number of kpoints in the k-path (depending on the ``kpath`` option)

**kpoints_distance** float specifying the distance between kpoints in the k-path (depending on the ``kpath`` option)

**kpoints_explicit** dictionary, which is used to create a new kpointlist in the input. The dictionary is unpacked and used as the argument for the :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_kpointlist()` function

**klistname** str, will be used to switch the used `kPointList` for fleur versions after Max5 (if ``kpath='auto'`` or ``mode='dos'``)

**sigma**, **emin**, **emax** floats specifying the energy grid for DOS calculations

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

.. _layout_banddos:

Supported input configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The FleurBandDosWorkChain workchain has several
input combinations that implicitly define the workchain layout. Only **scf**, **fleurinp** and
**remote** nodes control the behaviour, other input nodes are truly optional.
Depending on the setup of the given inputs, one of three supported scenarios will happen:

1. **scf**:

      SCF workchain will be submitted to converge the charge density which will
      be followed by the bandsturcture or DOS calculation. Depending on the inputs given in the SCF
      namespace, SCF will start from the structure or FleurinpData or will continue
      converging from the given remote_data (see details in :ref:`SCF WorkChain<scf_wc>`).

2. **remote**:

      Files which belong to the **remote** will be used for the direct submission of the band/DOS
      calculation. ``inp.xml`` file will be converted to FleurinpData and the charge density
      will be used as the charge density used in this calculation.

3. **remote** + **fleurinp**:

      Charge density which belongs to **remote** will be used as the charge density used in the
      band/DOS calculation, however the ``inp.xml`` from the **remote** will be ignored. Instead, the given **fleurinp** will be used.
      The aforementioned input files will be used for direct submission of the band/DOS
      calculation.

Other combinations of the input nodes **scf**, **fleurinp** and **remote** are forbidden.

.. warning::

  One *must* follow one of the supported input configurations. To protect a user from the
  workchain misbehaviour, an error will be thrown if one specifies e.g. both **scf** and **remote**
  inputs because in this case the intention of the user is not clear either he/she wants to
  converge a new charge density or use the given one.


Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python

    from aiida_fleur.tools.graph_fleur import draw_graph

    draw_graph(76867)

  .. figure:: /images/dos_76867.pdf
    :width: 100 %
    :align: center

Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Single node

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    # DOS calc
    plot_fleur(76867)

  .. figure:: /images/dos_plot.png
    :width: 60 %
    :align: center

    For the bandstructure visualization it depends on the File produced.
    Old bandstructure file:

  .. figure:: /images/bandstructure.png
    :width: 60 %
    :align: center

    Bandstructure ```band_dos.hdf``` file with l-like charge information:
    Band resolved bandstructure and fat-bands for the different channels.
    Spin and combinded DOS plus band structure visualizations are in progress...

  .. figure:: /images/Bands_colored.png
    :width: 60 %
    :align: center

  .. figure:: /images/band_s_like.png
    :width: 60 %
    :align: center

  .. figure:: /images/band_p_like.png
    :width: 60 %
    :align: center

  .. figure:: /images/band_d_like.png
    :width: 60 %
    :align: center

  .. figure:: /images/band_f_like.png
    :width: 60 %
    :align: center




  Multi node just does a bunch of single plots for now.

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    plot_fleur(dos_pk_list)


Example usage
^^^^^^^^^^^^^
  .. include:: code/banddos_submission.py
     :literal:


Output node example
^^^^^^^^^^^^^^^^^^^
 .. .. include:: /images/dos_wc_outputnode.py
  ..   :literal:

..  .. include:: /images/band_wc_outputnode.py
..     :literal:

Error handling
^^^^^^^^^^^^^^
In case of failure the Banddos WorkChain should throw one of the :ref:`exit codes<exit_codes>`:

+-----------+---------------------------------------------+
| Exit code | Reason                                      |
+===========+=============================================+
| 230       | Invalid workchain parameters ,please        |
|           | check input configuration                   |
+-----------+---------------------------------------------+
| 231       | Invalid input  configuration                |
|           | and fleur code nodes                        |
+-----------+---------------------------------------------+
| 233       | Invalid code node specified, check inpgen   |
|           | and fleur code nodes                        |
+-----------+---------------------------------------------+
| 235       | Input file modification failed              |
+-----------+---------------------------------------------+
| 236       |Input file was corrupted after  modifications|
+-----------+---------------------------------------------+
| 334       | SCF calculation failed                      |
+-----------+---------------------------------------------+
| 335       | Found no SCF remote repository.             |
+-----------+---------------------------------------------+

If your workchain crashes and stops in *Excepted* state, please open a new issue on the Github page
and describe the details of the failure.
