.. _base_relax_wc:

Fleur structure optimization Base workchain
-------------------------------------------

* **Current version**: 0.1.0
* **Class**: `~aiida_fleur.workflows.base_relax.FleurBaseRelaxWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.base_relax``
* **Workflow type**: Technical
* **Aim**: Stable execution of :py:class:`~aiida_fleur.workflows.relax.FleurRelaxWorkChain`

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.base_relax import FleurBaseRelaxWorkChain
    #or
    WorkflowFactory('fleur.base_relax')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
Optimizes the structure in a way the largest force is lower than a given threshold.

Wraps :ref:'relax_wc' and thus has the same input/output nodes.

Error handling
^^^^^^^^^^^^^^
A list of implemented error handlers:

To be documented.

Example usage
^^^^^^^^^^^^^
To be documented.
