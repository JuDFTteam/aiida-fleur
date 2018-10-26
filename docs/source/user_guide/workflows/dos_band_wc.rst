Fleur dos/band workflows
------------------------

These are two seperate workflows which are pretty similar so we treat them here together

* **Class**: :py:class:`~aiida_fleur.workflows.dos.Fleur_dos_wc` and  :py:class:`~aiida_fleur.workflows.dos.Fleur_band_wc`
* **String to pass to the** :py:func:`~aiida.orm.utils.WorkflowFactory`: ``fleur.dos``, ``fleur.band``
* **Workflow type**:  Workflow (lv 1)
* **Aim**: Calculate a density of states. Calculate a Band structure.
* **Compuational demand**: 1 ``Fleur Job calculation``
* **Database footprint**: Outputnode with information, full provenance, ``~ 10`` nodes
* **File repository footprint**: The ``JobCalculation`` run, plus the DOS or Bandstructure files
* **Additional Info**: Use alone.

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.dos import fleur_dos_wc
    #or 
    WorkflowFactory('fleur.dos')

    from aiida_fleur.workflows.band import fleur_band_wc
    #or 
    WorkflowFactory('fleur.band')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
  DOS:
  
  Calculates an Density of states (DOS) ontop of a given Fleur calculation (converged or not).
  
  Band:
  
  Calculates an electronic band structure ontop of a given Fleur calculation (converged or not).

  In the future we plan to add the posibility to converge a calculation before, and choose the kpaths automatic.
  This version should be able start simply from a crystal structure.

  Each of these workflows prepares/chances the Fleur input and manages one Fleur calculation.
  

    
Input nodes:
^^^^^^^^^^^^
  * ``fleur`` (:py:class:`~aiida.orm.Code`): Fleur code using the ``fleur.fleur`` plugin
  * ``wf_parameters`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): Some settings of the workflow behavior (e.g. number of kpoints, path, energy sampling and smearing, ...)
  * ``fleurinp`` (:py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, path 2): Fleur input data object representing the fleur input files.
  * ``remote_data`` (:py:class:`~aiida.orm.data.remote.RemoteData`, optional): The remote folder of the (converged) calculation whose output density is used as input for the DOS, or band structure run.
  
  * ``options``  (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): All options available in AiiDA, i.e resource specification, queue name, extras scheduler commands, ... 
  * ``settings`` (:py:class:`~aiida.orm.data.parameter.ParameterData`, optional): special settings for Fleur calculations, will be given like it is through to calculationss.
    
Returns nodes
^^^^^^^^^^^^^
  * ``output_dos_wc_para`` (:py:class:`~aiida.orm.data.parameter.ParameterData`): Information of the dos workflow results like success, last result node, list with convergence behavior
  * ``output_band_wc_para`` (:py:class:`~aiida.orm.data.parameter.ParameterData`): Information node from the band workflow
  * ``last_fleur_calc_output`` (:py:class:`~aiida.orm.data.parameter.ParameterData`) Output node of last Fleur calculation is returned.
    
Layout
^^^^^^
  .. figure:: /images/Workchain_charts_dos_wc.png
    :width: 50 %
    :align: center

Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python
    
    from aiida_fleur.tools.graph_fleur import draw_graph
    
    draw_graph(76867)
    
  .. figure:: /images/dos_76867.pdf
    :width: 100 %
    :align: center
        
Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Single node
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    # DOS calc
    plot_fleur(76867)

  .. figure:: /images/dos_plot.png
    :width: 60 %
    :align: center

    For the bandstructure visualization it depends on the File produced.
    Old bandstructure file:
    
  .. figure:: /images/bandstructure.png
    :width: 60 %
    :align: center

    Bandstructure ```band_dos.hdf``` file with l-like charge information:
    Band resolved bandstructure and fat-bands for the different channels. 
    Spin and combinded DOS plus band structure visualizations are in progress...

  .. figure:: /images/Bands_colored.png
    :width: 60 %
    :align: center
    
  .. figure:: /images/band_s_like.png
    :width: 60 %
    :align: center

  .. figure:: /images/band_p_like.png
    :width: 60 %
    :align: center
    
  .. figure:: /images/band_d_like.png
    :width: 60 %
    :align: center
    
  .. figure:: /images/band_f_like.png
    :width: 60 %
    :align: center
    

    

  Multi node just does a bunch of single plots for now.
  
  .. code-block:: python
    
    from aiida_fleur.tools.plot import plot_fleur
    
    plot_fleur(dos_pk_list)
     

Example usage
^^^^^^^^^^^^^
  .. include:: ../../../../examples/tutorial/workflows/tutorial_submit_dos.py
     :literal:

     
Output node example
^^^^^^^^^^^^^^^^^^^
 .. .. include:: /images/dos_wc_outputnode.py
  ..   :literal:
     
..  .. include:: /images/band_wc_outputnode.py
..     :literal:
     
Error handling
^^^^^^^^^^^^^^
  Still has to be documented
  
  Warning if parent calculation was not converged.