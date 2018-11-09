Fleur core-hole workflow
------------------------

Class name, import from:
  ::

    from aiida_fleur.workflows.corehole import fleur_corehole_wc
    #or 
    WorkflowFactory('fleur.corehole')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
  Converges the charge density and/or the total energy of a given system, 
  or stops because the maximum allowed retries are reached.
    
  This workflow manages none to one inpgen calculation and one to several Fleur calculations.
  It is one of the most core workflows and often deployed as subworkflow.
  
  .. note::
    The fleur_wc_sc per default determines the calculation resources required for the given system and
    with what hybrid parallelisation to launch Fleur. The resources in the option node given are the maximum 
    resources the workflow is allowed to allocate for one simulation (job).
    You can turn off this feature by setting ``determine_resources = False`` in the ``wf_parameters``.
    
Input nodes
^^^^^^^^^^^
  * ``fleur`` (*aiida.orm.Code*): Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen`` (*aiida.orm.Code*): Inpgen code using the ``fleur.inpgen`` plugin
  * ``wf_parameters`` (*ParameterData*, optional): Some settings of the workflow behavior (e.g. convergence criterion, maximum number of Fleur jobs..)
  
  * ``structure`` (*StructureData*, path 1): Crystal structure data node.
  * ``calc_parameters`` (*str*, optional): Longer description of the workflow
    
  * ``fleurinp`` (*FleurinpData*, path 2): Label of the workflow
  * ``remote_data`` (*RemoteData*, optional): The remote folder of the (converged) calculation whose output potential is used as input for the DOS run

  * ``settings`` (*ParameterData*, optional): special settings for Fleur calculations, will be given like it is through to calculationss.
    
Returns nodes
^^^^^^^^^^^^^
  * ``output_scf_wc_para`` (*ParameterData*): Information of workflow results like success, last result node, list with convergence behavior

  * ``fleurinp`` (*FleurinpData*) Input node used is retunred.
  * ``last_fleur_calc_output`` (*ParameterData*) Output node of last Fleur calculation is returned.
    
Layout
^^^^^^
  .. figure:: /images/Workchain_charts_corehole_wc.png
    :width: 50 %
    :align: center

Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python
    
    from aiida_fleur.tools.graph_fleur import draw_graph
    
    draw_graph(30528)
    
  .. figure:: /images/corehole_si_30528.pdf
    :width: 100 %
    :align: center
        
Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Currently there is no visualization directly implemented for plot fleur.
  Through there 

Example usage
^^^^^^^^^^^^^
  .. include:: ../../../../examples/tutorial/workflows/tutorial_submit_scf.py
     :literal:

     
Output node example
^^^^^^^^^^^^^^^^^^^
  .. include:: /images/scf_wc_outputnode.py
     :literal:

Error handling
^^^^^^^^^^^^^^
  Still has to be documented