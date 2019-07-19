Fleur Workchains
================

General design
--------------

All of the WorkChains have a similar interface and they share several common input nodes.
First, all of the workflows accept FLEUR and inpgen code nodes as an input. inpgen node is not
required since sometimes there is no need to generate a new inp.xml file.

There is always an optional ``wf_parameters``:
:py:class:`~aiida.orm.Dict` node for controlling the workflow which
has some reasonable defaults. It contains all the parameters related to physical aspects of the
workchain. That is why the content of
``wf_parameters`` vary between different workchains.

.. note::

    There is always an ``inpxml_changes``
    nested list that can be specified in the ``wf_parameters``. This list can be used to apply any
    supported changes into inp.xml that do not have a shortcut in the workchain.

The other common input is an ``options``: :py:class:`~aiida.orm.Dict` node
where the technical parameters (AiiDA options) are specified i.e resources, queue name and so on.

Regarding an input crystal structure, it can be set in two ways in the most of the workflows:

    1. Provide a ``structure``: :py:class:`~aiida.orm.StructureData` node
       and an optional ``calc_parameters``: :py:class:`~aiida.orm.Dict`.
       It this case an inpgen code node is required. The workflow will call inpgen calculation and
       create a new FleurinpData that will be used in the workchain. You can find more
       information in the inpgen calculation section.
    2. Provide a ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` node
       which contains a complete input for a FLEUR calculation.

Next, a ``remote_data``: :py:class:`~aiida.orm.RemoteData`
can be optionally given to use the last charge density or other files from this previous
calculation. For example, it is used when one wants to start a SCF calculation from a given charge
density to speed up the calculation.

Most of the workchains return a workflow specific *ParameterData*
(:py:class:`~aiida.orm.Dict`) node named ``output_name_wc_para``
which contains the main results and some information about the workchain.

There are additional workflow specific input and output nodes, please read the
documentation of a particular workchain that you are interested in.

All of the workchains are split into the groups. First, we separate *technical* and
*scientific* workflows. This separation is purely subjective: *technical* workchains tend to be
less complex and represent basic routine tasks that people usually encounter. *Scientific*
workflows make a particular physical task which is more specific to the particular project.

There are the sub-group of the force theorem calculations
and their self-consistent analogs in the scientific workchains group.

.. note::

    The ``plot_fleur`` function provides a quick visualization for every workflow node or node list.
    Inputs are *uuid*, *pk*, *workchain* nodes or *ParameterData* (workchain output) nodes.

Basic (Technical) Workchains
------------------------------------------

Here describe the basic workflows and how to use them. (Beyond the source code documentation)

.. toctree::
   :maxdepth: 2

   ./base_wc
   ./scf_wc
   ./dos_band_wc
   ./eos_wc
   ./relax_wc


More advanced (Scientific) Workchains
-----------------------------------------------

.. toctree::
   :maxdepth: 2

   ./initial_cls_wc
   ./corehole_wc


Force-theorem sub-group
,,,,,,,,,,,,,,,,,,,,,,,,,,,
.. toctree::
   :maxdepth: 2

   ./ssdisp_wc
   ./dmi_wc
   ./mae_wc


Self-consistent sub-group
,,,,,,,,,,,,,,,,,,,,,,,,,
.. toctree::
   :maxdepth: 2

   ./ssdisp_conv_wc
   ./mae_conv_wc
