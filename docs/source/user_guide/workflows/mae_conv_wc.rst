.. _mae_conv_wc:

Fleur self-consistent Magnetic Anisotropy Energy workchain
----------------------------------------------------------

* **Class**: :py:class:`~aiida_fleur.workflows.mae.FleurMaeConvWorkChain`
* **String to pass to the** :py:func:`~aiida.orm.utils.WorkflowFactory`: ``fleur.mae_conv``
* **Workflow type**: Scientific workchain, self-consistent subgroup
* **Aim**: Calculate Magnetic Anisotropy Energies along given spin quantization axes
* **Computational demand**: A ``Fleur SCF WorkChain`` for each SQA
* **Database footprint**: Outputnode with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes
* **File repository footprint**: no addition to the ``JobCalculations`` run

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.mae_conv import FleurMaeConvWorkChain
    #or
    WorkflowFactory('fleur.ma_conv')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
This workchain calculates Magnetic Anisotropy Energy over a given set of spin-quantization axes.
Charge density is converged for all SQAs which means
a FleurScfWorkChain is submitted for each SQA. This requires more computational cost than
FleurMaeWorkChain but gives more accurate results.

Input nodes
^^^^^^^^^^^

  * ``fleur``: :py:class:`~aiida.orm.Code` - Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen``, optional: :py:class:`~aiida.orm.Code` - Inpgen code using the ``fleur.inpgen``
    plugin
  * ``wf_parameters``: :py:class:`~aiida.orm.data.parameter.ParameterData`, optional - Settings
    of the workflow behavior
  * ``structure``: :py:class:`~aiida.orm.data.structure.StructureData`, optional: Crystal structure
    data node.
  * ``calc_parameters``: :py:class:`~aiida.orm.data.parameter.ParameterData`, optional -
    FLAPW parameters, used by inpgen
  * ``options``: :py:class:`~aiida.orm.data.parameter.ParameterData`, optional - AiiDA options
    (queues, cpus)

Returns nodes
^^^^^^^^^^^^^

  * ``out`` (*ParameterData*): Information of workflow results like success,
    last result node, list with convergence behavior

Default inputs
^^^^^^^^^^^^^^
Workflow parameters.

.. code-block:: python

    wf_parameters_dict = {
        'fleur_runmax': 10,
        'sqas': {'label' : [0.0, 0.0]},
        'alpha_mix': 0.05,
        'density_converged': 0.00005,
        'serial': False,
        'itmax_per_run': 30,
        'soc_off': [],
        'inpxml_changes': [],
    }


Layout
^^^^^^
Still has to be documented


Example usage
^^^^^^^^^^^^^
Still has to be documented

Output node example
^^^^^^^^^^^^^^^^^^^
Still has to be documented

Error handling
^^^^^^^^^^^^^^
Still has to be documented
