.. _create_magnetic_wc:

Fleur Create Magnetic Film workchain
--------------------------------------

* **Current version**: 0.1.0
* **Class**: :py:class:`~aiida_fleur.workflows.create_magnetic_film.FleurCreateMagneticWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.create_magnetic``
* **Workflow type**: Scientific workchain

.. contents::
    :depth: 2

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.create_magnetic_film import FleurCreateMagneticWorkChain
    #or
    WorkflowFactory('fleur.create_magnetic')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
The workchain constructs a relaxed film structure which is ready-to-use in the subsequent
magnetic workchains, such as :ref:`DMI<dmi_wc>`, :ref:`MAE<mae_wc>` or :ref:`SSDisp<ssdisp_wc>`
workchains.

The main inputs include information about the substrate (structure type, miller indices, element)
and deposited material. The main logic of the workchain is depicted on the figure below:

.. image:: images/create_magnetic_scheme.png
    :width: 100%
    :align: center

First, workchains uses :ref:`EOS workchain<eos_wc>` to find the equilibrium lattice parameters for
the substrate. For now only bcc and fcc substrate lattices are supported. Note, the algorithm always
uses conventional unit cells e.g. one gets 4 atoms in the unit cell for fcc lattice (see the figure
above).

After that, the workchain constructs a film which will be used for interlayer distance
relaxation via the :ref:`relaxation workchain<relax_wc>`. The algorithm creates a film using given
miller indices and the ground state lattice constant and replaces some layers with another
elements given
in the input. For now only single-element layer replacements are possible i.e. each resulting layer
can be a single element. It is not possible to create e.g. B-N monolayer using this workchain. If
we refer to the figure above, in ideal case one constructs a structure with an inversion or
z-reflection symmetry to calculate interlayer distances 1-4. However, the workchain does not
ensure an inversion or z-reflection symmetry, that is user responsibility to make it. For
instance, if you want to achieve one of these symmetries you should pass positive and negative
numbers of layer in the replacements dictionary of the wf parameters, see an example in
:ref:`defaults<defaults_para_create>`.

.. note::

    Again, z-reflection or inversion symmetries are not ensured by the workchain even if you
    specify symmetric replacements. Sometimes you need to remove a few layers before replacements.
    For example, consider the case of fcc (110) film: if ``size`` is equal to (1, 1, 4) there are
    will
    be 8 layers in the template before the replacements since there are 2 layers in the unit cell.
    That means the x,y position of the first atom
    are equal to (0.0, 0.0) when the 8th atom has (0.5, 0.5) coordinates. Thus, to achieve the
    z-reflection symmetry one needs to remove the 8th layer by specifying ``'pop_last_layers' : 1``
    in the wf parameters.

Finally, using the result of the
relaxation workchain, a magnetic structure having no z-reflection (or inversion) symmetry is
created. For this the workchain takes first N layers from the relaxed structure and attaches M
substrate layers to the bottom. The final structure is z-centralised.

.. _exposed: https://aiida.readthedocs.io/projects/aiida-core/en/latest/working/workflows.html#working-workchains-expose-inputs-outputs

Input nodes
^^^^^^^^^^^

The :py:class:`~aiida_fleur.workflows.create_magnetic_film.FleurCreateMagneticWorkChain` employs
`exposed`_ feature of the AiiDA-core, thus inputs for the
:ref:`EOS<eos_wc>` and :ref:`relaxation<relax_wc>` workchains should be passed in the namespaces
``eos`` and ``relax`` correspondingly (see :ref:`example of usage<example_use_create_magnetic>`).

+-----------------+-----------------------------+-------------------------------------+----------+
| name            | type                        | description                         | required |
+=================+=============================+=====================================+==========+
| wf_parameters   | :py:class:`~aiida.orm.Dict` | Settings of the workchain           | no       |
+-----------------+-----------------------------+-------------------------------------+----------+
| eos_output      | :py:class:`~aiida.orm.Dict` | :ref:`EOS<eos_wc>` output dictionary| no       |
+-----------------+-----------------------------+-------------------------------------+----------+

Similarly to other workchains,
:py:class:`~aiida_fleur.workflows.create_magnetic_film.FleurCreateMagneticWorkChain` behaves
differently depending on the input nodes setup. The list of supported input configurations is
given in the section :ref:`layout_create_magnetic`.

.. _defaults_para_create:

Workchain parameters and its defaults
.....................................

``wf_parameters``
,,,,,,,,,,,,,,,,,

``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
keys and their defaults are listed below:

.. literalinclude:: code/create_magnetic_parameters.py


Output nodes
^^^^^^^^^^^^^

  * ``magnetic_structure``: :py:class:`~aiida.orm.StructureData`- the relaxed film structure.

.. _layout_create_magnetic:

Supported input configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CreateMagnetic workchain has several
input combinations that implicitly define the workchain layout. Depending
on the setup of the inputs, one of four supported scenarios will happen:

1. **eos_output**:

      If **eos_output** is given and ``wf_parameters['eos_needed']`` is ``True``, the
      workchain omits the EOS step and uses data from the given EOS workchain output dictionary.
      Thus all other parameters given for EOS workchain are ignored.


Error handling
^^^^^^^^^^^^^^
A list of implemented exit codes:

+------+------------------------------------------------------------------------------------------+
| Code | Meaning                                                                                  |
+======+==========================================================================================+
| 401  | Specified substrate is not bcc or fcc, only them are supported                           |
+------+------------------------------------------------------------------------------------------+
| 402  | eos_output was not specified, however, 'eos_needed' was set to True                      |
+------+------------------------------------------------------------------------------------------+

.. _example_use_create_magnetic:

Example usage
^^^^^^^^^^^^^

  .. literalinclude:: code/create_magnetic_submission.py
