General design
--------------

Overall the interfaces (input) for most Fleur workflows are quite similar.
There is always an optional ``wf_parameters`` (:py:class:`~aiida.orm.data.structure.ParamterData`) node for controlling the workflow, which has some reasonable defaults. 
Also all workflows take an ``options`` (:py:class:`~aiida.orm.data.structure.ParamterData`) node, where the usual AiiDA options are specified i.e resources, queue name and so on.
The crystal structure can be provided in two ways to the most workflows.

The first way is to provide a ``structure`` (:py:class:`~aiida.orm.data.structure.StructureData`) node and optional a ``calc_parameters`` (:py:class:`~aiida.orm.data.structure.ParamterData`)
node, to enforce, specify the FLAPW parameters for the given crystal structure.
Otherwise the default FLAPW constructed by inpgen and the Fleur code are used.

The second way is to provide an ``fleurinp`` (:py:class:`~aiida_fleur.data.fleurinp.FleurinpData`) node, which contains
a complete input for a fleur calculation. If you have to specify something special in the input.
This way might be more convinient for your case.
In this way also a ``remote_data`` (:py:class:`~aiida.orm.data.remote.RemoteData`) node can be optionally given, to use the last charge density or other files from this previous calculation.

Most workchains return an workflow specific *ParameterData* (:py:class:`~aiida.orm.data.structure.ParamterData`) node, named ``output_name_wc_para``, 
which contains the main results and some information about the workchain.

There are of cause additional workflow specific input and output nodes.

Also the ``plot_fleur`` function provides a quick visualization for every workflow node or node list.
Inputs are *uuid*, *pk*, *workchain* nodes or *ParameterData* (workchain output) nodes.


.. .. toctree::
..   :maxdepth: 1
   
..   ./scf_wc
..   ./dos_band_wc
..   ./eos_wc
..   ./initial_cls_wc
..   ./corehole_wc
   
   
.. #. Fleur scf
.. #. Fleur dos
.. #. Fleur band
.. #. Fleur eos
.. #. Fleur initial corelevel shifts
.. #. Fleur corehole