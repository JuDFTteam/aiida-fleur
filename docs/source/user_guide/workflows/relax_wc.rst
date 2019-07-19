.. _relax_wc:

Fleur structure optimization workchain
--------------------------------------

* **Class**: :py:class:`~aiida_fleur.workflows.relax.FleurRelaxWorkChain`
* **String to pass to the** :py:func:`~aiida.orm.utils.WorkflowFactory`: ``fleur.relax``
* **Workflow type**: Basic workflow
* **Aim**: Structure optimization of a given structure
* **Computational demand**: Several :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain`
* **Database footprint**: Output node with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.relax import FleurRelaxWorkChain
    #or
    WorkflowFactory('fleur.relax')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
Optimizes the structure in a way the largest force is lower than a given threshold.

Uses :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain` to converge forces first,
checks if the largest force is smaller than the
threshold. If the largest force is bigger, submits a new
:py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain` for next step structure
proposed by FLEUR.

Input nodes
^^^^^^^^^^^

  * ``fleur``: :py:class:`~aiida.orm.Code` - Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen``, optional: :py:class:`~aiida.orm.Code` - Inpgen code using the ``fleur.inpgen``
    plugin
  * ``wf_parameters``: :py:class:`~aiida.orm.Dict`, optional - Settings
    of the workflow behavior
  * ``structure``: :py:class:`~aiida.orm.StructureData`, optional: Crystal structure
    data node.
  * ``calc_parameters``: :py:class:`~aiida.orm.Dict`, optional -
    FLAPW parameters, used by inpgen
  * ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, optional: Fleur input data
    object representing the fleur input files
  * ``remote_data``: :py:class:`~aiida.orm.data.remote.RemoteData`, optional - The remote folder of
    the previous calculation
  * ``options``: :py:class:`~aiida.orm.Dict`, optional - AiiDA options
    (queues, cpus)
  * ``settings``: :py:class:`~aiida.orm.Dict`, optional - special settings

Returns nodes
^^^^^^^^^^^^^

  * ``out``: :py:class:`~aiida.orm.Dict` - Information of workflow results
  * ``optimized_structure``: :py:class:`~aiida.orm.StructureData` - Optimized structure

Default inputs
^^^^^^^^^^^^^^
Workflow parameters.

.. code-block:: python

    wf_parameters_dict = {'fleur_runmax': 4,       # needed for SCF
                   'alpha_mix': 0.015,             # Sets alpha mixing parameter
                   'relax_iter': 5,                # Maximum number of optimization iterations
                   'force_criterion': 0.001,       # Sets the threshold of the largest force
                   'force_converged' : 0.002,      # needed for SCF
                   'serial' : False,               # needed for SCF
                   'force_dict': {'qfix': 2,       # needed for SCF
                                  'forcealpha': 0.5,
                                  'forcemix': 2},
                   'itmax_per_run' : 30,           # needed for SCF
                   'inpxml_changes' : [],          # needed for SCF
                   }

Layout
^^^^^^
Geometry optimization workchain has several
input combinations that implicitly define the workchain layout. Depending
on the setup of the inputs, one of four supported scenarios will happen:

1. **fleurinp**:

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation.

2. **fleurinp** + **parent_folder** (FLEUR):

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Moreover, initial charge density will be
      copied from the folder of the parent calculation.

3. **parent_folder** (FLEUR):

      inp.xml file and initial
      charge density will be copied from the folder of the parent FLEUR calculation.

4. **structure**:

      inpgen code will be used to generate a new **fleurinp** using a given structure.

Example usage
^^^^^^^^^^^^^

Output node example
^^^^^^^^^^^^^^^^^^^

Error handling
^^^^^^^^^^^^^^
  Still has to be documented
