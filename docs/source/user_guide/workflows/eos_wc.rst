Fleur equation of states (eos) workflows
----------------------------------------

Class name, import from:
  ::

    from aiida_fleur.workflows.eos import fleur_eos_wc
    #or 
    WorkflowFactory('fleur.eos')

Description/Purpose:
  Calculates an equation of state for a given crystal structure.
  The volume of the unit cell is varied by a certain scale.
  All these scale points are then converged with the same FLAPW parameters with the 
  ``fleur_scf_wc``.
  
  To the resulting total energy of this systems a Birch–Murnaghan equation of state is 
  fitted per default to extract the volume with the lowest energy and the bulk modulus.
  Other fit options are also available.
    
Inputs:
  * ``fleur`` (*aiida.orm.Code*): Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen`` (*aiida.orm.Code*): Inpgen code using the ``fleur.inpgen`` plugin
  * ``wf_parameters`` (*ParameterData*, optional): Some settings of the workflow behavior (e.g. number of points, scaling, convergence criterion, ...)
    The number of points should be at least 5, the default is 9.
  * ``structure`` (*StructureData*, path 1): Crystal structure data node.
  * ``calc_parameters`` (*str*, optional): Longer description of the workflow

  * ``options``  (*ParameterData*, optional): All options available in AiiDA, i.e resource specification, queue name, extras scheduler commands, ... 
  * ``settings`` (*ParameterData*, optional): special settings for Fleur calculations, will be given like it is through to calculationss.
    
Returns nodes:
  * ``output_eos_wc_para`` (*ParameterData*): Information of workflow results like success, list with convergence behavior
  * ``output_eos_wc_structure`` (*StructureData*) Crystal structure with the volume of the lowest total energy.

        
Layout:
  .. figure:: /images/Workchain_charts_eos_wc.png
    :width: 50 %
    :align: center

Database Node graph:
  .. code-block:: python
    
    from aiida_fleur.tools.graph_fleur import draw_graph
    
    draw_graph(49670)
    
  .. figure:: /images/eos_49670.pdf
    :width: 100 %
    :align: center
        
Plot_fleur visualization:
  Single node
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    plot_fleur(49670)
    
  .. figure:: /images/plot_fleur_scf1.png
    :width: 60 %
    :align: center

  Multi node
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    plot_fleur(scf_pk_list)
     
  .. figure:: /images/plot_fleur_scf_m1.png
    :width: 60 %
    :align: center


Example usage:
  .. include:: ../../../../examples/tutorial/workflows/tutorial_submit_eos.py
     :literal:

     
Output node example:
  .. include:: /images/eos_wc_outputnode.py
     :literal:

Error handling:
  Still has to be documented