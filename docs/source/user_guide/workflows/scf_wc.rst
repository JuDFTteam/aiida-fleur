Fleur self-consistency field workflow
-------------------------------------

* **Class**: :py:class:`~aiida_fleur.workflows.scf.Fleur_scf_wc`
* **String to pass to the** :py:func:`~aiida.orm.utils.WorkflowFactory`: ``fleur.scf``
* **Workflow type**: Base workflow (lv 0)
* **Aim**: Manage FLEUR SCF convergence
* **Compuational demand**: 1-4 ``Fleur Job Calculations`` in serial
* **Database footprint**: Outputnode with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes
* **File repository footprint**: no addition to the ``JobCalculations`` run
* **Additional Info**: Use alone or as subworkflow

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.scf import fleur_scf_wc
    #or 
    WorkflowFactory('fleur.scf')

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

  * ``fleur`` (:py:class:`~aiida.orm.Code`): Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen`` (:py:class:`~aiida.orm.Code`): Inpgen code using the ``fleur.inpgen`` plugin
  * ``wf_parameters`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): Some settings of the workflow behavior (e.g. convergence criterion, maximum number of Fleur jobs..)
  
  * ``structure`` (:py:class:`~aiida.orm.data.structure.StructureData, path 1): Crystal structure data node.
  * ``calc_parameters`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): Specify the FLAPW parameters, used by inpgen
    
  * ``fleurinp`` (:py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, path 2): Fleur input data object representing the fleur input files.
  * ``remote_data`` (:py:class:`~aiida.orm.data.remote.RemoteData`, optional): The remote folder of the (converged) calculation whose output density is used as input for the DOS run
  
  * ``options``  (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): All options available in AiiDA, i.e resource specification, queue name, extras scheduler commands, ... 
  * ``settings`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): special settings for Fleur calculations, will be given like it is through to calculationss.
    
Returns nodes
^^^^^^^^^^^^^

  * ``output_scf_wc_para`` (*ParameterData*): Information of workflow results like success, last result node, list with convergence behavior

  * ``fleurinp`` (*FleurinpData*) Input node used is retunred.
  * ``last_fleur_calc_output`` (*ParameterData*) Output node of last Fleur calculation is returned.
 
Default inputs
^^^^^^^^^^^^^^
Workflow paremters.

.. code-block:: python

    wf_parameters_dict = {'fleur_runmax': 4,       # Maximum number of fleur jobs/starts (default 30 iterations per start)
                   'density_criterion' : 0.00002,  # Stop if charge denisty is converged below this value
                   'energy_criterion' : 0.002,     # if converge energy run also this total energy convergered below this value
                   'converge_density' : True,      # converge the charge density
                   'converge_energy' : False,      # converge the total energy (usually converged before density)
                   #'caching' : True,              # AiiDA fastforwarding (currently not there yet)
                   'serial' : False,               # execute fleur with mpi or without
                   'itmax_per_run' : 30,           # Maximum iterations run for one Fleur job
                   'inpxml_changes' : [],          # (expert) List of further changes applied to the inp.xml after the inpgen run
                   }                               # tuples (function_name, [parameters]), have to be the function names supported by fleurinpmodifier
                          
   
Layout
^^^^^^

  .. figure:: /images/Workchain_charts_scf_wc.png
    :width: 50 %
    :align: center

Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python
    
    from aiida_fleur.tools.graph_fleur import draw_graph
    
    draw_graph(50816)
    
  .. figure:: /images/scf_50816.pdf
    :width: 100 %
    :align: center
        
Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Single node
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    plot_fleur(50816)
    
  .. figure:: /images/plot_fleur_scf1.png
    :width: 60 %
    :align: center

  .. figure:: /images/plot_fleur_scf2.png
    :width: 60 %
    :align: center

  Multi node
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    plot_fleur(scf_pk_list)
     
  .. figure:: /images/plot_fleur_scf_m1.png
    :width: 60 %
    :align: center

  .. figure:: /images/plot_fleur_scf_m2.png
    :width: 60 %
    :align: center

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