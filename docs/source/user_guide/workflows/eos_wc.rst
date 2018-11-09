Fleur equation of states (eos) workflows
----------------------------------------


* **Class**: :py:class:`~aiida_fleur.workflows.eos.Fleur_eos_wc`
* **String to pass to the** :py:func:`~aiida.orm.utils.WorkflowFactory`: ``fleur.eos``
* **Workflow type**:  Workflow (lv 1)
* **Aim**: Vary the cell volume, to fit an equation of states, (Bulk modulus, ...)
* **Compuational demand**: 5-10 ``Fleur SCF workchains`` in parallel
* **Database footprint**: Outputnode with information, full provenance, ``~ (10+10*FLEUR Jobs)*points`` nodes
* **File repository footprint**: no addition to the ``JobCalculations`` run
* **Additional Info**: Use alone.

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.eos import fleur_eos_wc
    #or 
    WorkflowFactory('fleur.eos')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
  Calculates an equation of state for a given crystal structure.
  The volume of the unit cell is varied by a certain scale.
  All these scale points are then converged with the same FLAPW parameters with the 
  ``fleur_scf_wc``.
  
  To the resulting total energy of this systems a Birch–Murnaghan equation of state is 
  fitted per default to extract the volume with the lowest energy and the bulk modulus.
  Other fit options are also available.
    
Input nodes
^^^^^^^^^^^
  * ``fleur`` (:py:class:`~aiida.orm.Code`): Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen`` (:py:class:`~aiida.orm.Code`): Inpgen code using the ``fleur.inpgen`` plugin
  * ``wf_parameters`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): Some settings of the workflow behavior (e.g. number of points, scaling, convergence criterion, ...)
    The number of points should be at least 5, the default is 9.
  * ``structure`` (:py:class:`~aiida.orm.data.structure.StructureData`, path 1): Crystal structure data node.
  * ``calc_parameters`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): Longer description of the workflow

  * ``options``  (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): All options available in AiiDA, i.e resource specification, queue name, extras scheduler commands, ... 
  * ``settings`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): special settings for Fleur calculations, will be given like it is through to calculationss.
    
Returns nodes
^^^^^^^^^^^^^
  * ``output_eos_wc_para`` (:py:class:`~aiida.orm.data.parameter.ParameterData`): Information of workflow results like success, list with convergence behavior
  * ``output_eos_wc_structure`` (:py:class:`~aiida.orm.data.structure.StructureData`) Crystal structure with the volume of the lowest total energy.

        
Layout
^^^^^^
  .. figure:: /images/Workchain_charts_eos_wc.png
    :width: 50 %
    :align: center

Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python
    
    from aiida_fleur.tools.graph_fleur import draw_graph
    
    draw_graph(49670)
    
  .. figure:: /images/eos_49670.pdf
    :width: 100 %
    :align: center
        
Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Single node
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    plot_fleur(49670)
    
  .. figure:: /images/plot_fleur_eos_sn.png
    :width: 60 %
    :align: center

  Multi node
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    plot_fleur(eos_pk_list)
     
  .. figure:: /images/plot_fleur_eos_mn.png
    :width: 60 %
    :align: center


Example usage
^^^^^^^^^^^^^
  .. include:: ../../../../examples/tutorial/workflows/tutorial_submit_eos.py
     :literal:

     
Output node example
^^^^^^^^^^^^^^^^^^^
  .. include:: /images/eos_wc_outputnode.py
     :literal:

Error handling
^^^^^^^^^^^^^^
  Still has to be documented...
  
  Total energy check:
  
  The workflow quickly checks the behavior of the total energy for outliers.
  Which might occure, because the choosen FLAPW parameters might not be good for 
  all volumes. Also local Orbital setup and so on might matter.
  
  * Not enough points for fit
  * Some calculations did not convergere
  * Volume ground state does not lie in the calculated interval, interval refinement
  
