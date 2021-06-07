.. _init_cl_wc:

* **Current version**: 0.4.0

Fleur initial core-level shifts workflow
----------------------------------------


Class name, import from:
  ::

    from aiida_fleur.workflows.initial_cls import FleurInitialCLSWorkChain
    #or
    WorkflowFactory('fleur.init_cls')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
The initial-state workflow `fleur_initial_cls_wc` calculates core-level shifts of a 
system with respect to the elemental references via normal SCF calculations. 
If required, the SCF calculations of the corresponding elemental references are also 
managed by the workflow. Furthermore, the workflow extracts the enthalpy of formation for 
the investigated compound from these SCF runs. The workflow calculates core-level shifts (CLS) as the
difference of Kohn-Sham core-level energies with respect to the respected Fermi level. 
  
This workflow manages none to one inpgen calculation and one to several Fleur calculations.
It is one of the most core workflows and often deployed as sub-workflow.
  
.. note::
  To minimize uncertainties on CLS it is important that the compound as well as the reference systems are
  calculated with the same atomic parameters (muffin-tin radius, radial grid points and spacing, radial basis cutoff). 
  The workflow tests for this equality and tries to assure it, though it does not know
  what is a good parameter set nor if the present set works well for both systems. 
  It is currently best practice to enforce the FLAPW parameters used within the workflow, i.e.,
  provide them as input for the system as for the references.
  For low high-throughput failure rates and smallest data footprint we advice to calculate 
  the references first alone and parse a converged calculation as a reference, 
  that way references are not rerun and produce less overhead.
  Otherwise one can also turn on `caching` in AiiDA which will save the recalculation of the references, 
  but won't decrease their data footprint.

Layout
^^^^^^
  .. figure:: /images/Workchain_charts_initial_state.png
    :width: 50 %
    :align: center


Input nodes
^^^^^^^^^^^
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| name            | type                                               | description                             | required |
+=================+====================================================+=========================================+==========+
| inpgen          | :py:class:`~aiida.orm.Code`                        | Inpgen code                             | yes      |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleur           | :py:class:`~aiida.orm.Code`                        | Fleur code                              | yes      |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| wf_parameters   | :py:class:`~aiida.orm.Dict`                        | Settings of the workchain               | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleurinp        | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`| :ref:`FLEUR input<fleurinp_data>`       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| structure       | :py:class:`~aiida.orm.StructureData`               | Crystal structure                       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| calc_parameters | :py:class:`~aiida.orm.Dict`                        | FLAPW parameters for given structure    | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| options         | :py:class:`~aiida.orm.Dict`                        | AiiDA options (computational resources) | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+

More details:
  * ``fleur`` (*aiida.orm.Code*): Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen`` (*aiida.orm.Code*): Inpgen code using the ``fleur.inpgen`` plugin
  * ``wf_parameters`` (*Dict*, optional): Some settings of the workflow behavior 

  * ``structure`` (*StructureData*, path 1): Crystal structure data node.
  * ``calc_parameters`` (*Dict*, optional): Longer description of the workflow

  * ``fleurinp`` (*FleurinpData*, path 2): Label of the workflow

Workchain parameters and its defaults
.....................................

``wf_parameters``
,,,,,,,,,,,,,,,,,

``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
keys and their defaults are listed below:

.. literalinclude:: code/initial_cls_parameters.py

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

Returns nodes
^^^^^^^^^^^^^

The table below shows all the possible output nodes of the fleur_initial_cls_wc workchain.

+-----------------------------+--------------------------------------------------+--------------------------------------------------+
| name                        | type                                             | comment                                          |
+=============================+==================================================+==================================================+
| output_initial_cls_wc_para  | :py:class:`~aiida.orm.Dict`                      | Link to last FleurCalculation output dict        |
+-----------------------------+--------------------------------------------------+--------------------------------------------------+

More details:

  * ``output_initial_cls_wc_para``: :py:class:`~aiida.orm.Dict` -  Main results of the workchain. Contains
    core-level shifts, band gaps, core-levels, atom-type information, 
    errors, warnings, other information. An example:

    .. literalinclude:: code/initial_cls_wc_outputnode.py


Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Single node

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    plot_fleur(50816)


Example usage
^^^^^^^^^^^^^
  .. include:: code/initial_cls_submission.py
     :literal:



Error handling
^^^^^^^^^^^^^^
  Still has to be documented.

  So far only the input is checked. All other errors are currently not handled.
  The SCF sub-workchain comes with its own error handling of course.
