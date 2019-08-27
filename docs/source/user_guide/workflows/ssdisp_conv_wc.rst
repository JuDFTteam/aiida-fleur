.. _ssdisp_conv_wc:

Fleur Spin-Spiral Dispersion workchain
--------------------------------------

* **Current version**: 0.1.0
* **Class**: :py:class:`~aiida_fleur.workflows.ssdisp_conv.FleurSSDispConvWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.ssdisp_conv``
* **Workflow type**: Scientific workchain, self-consistent subgroup
* **Aim**: Calculate spin-spiral energy dispersion over given q-points.
* **Computational demand**: A ``Fleur SCF WorkChain`` for each q-point to calculate.
* **Database footprint**: Outputnode with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes
* **File repository footprint**: no addition to the ``JobCalculations`` run
* **Additional Info**: Use alone or as sub-workflow

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.ssdisp_conv import FleurSSDispConvWorkChain
    #or
    WorkflowFactory('fleur.ssdisp_conv')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
This workchain calculates spin spiral energy  dispersion over a given set of q-points.
Charge density is converged for all given q-points which means
a FleurScfWorkChain is submitted for each q-point. This requires more computational cost than
FleurMaeWorkChain but gives more accurate results.

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
  * ``options``: :py:class:`~aiida.orm.Dict`, optional - AiiDA options
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
        'beta': {'all' : 1.57079},
        'q_vectors': {'label': [0.0, 0.0, 0.0],
                      'label2': [0.125, 0.0, 0.0]
                     },
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
