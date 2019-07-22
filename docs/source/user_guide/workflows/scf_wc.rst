.. _scf_wc:

Fleur self-consistency field workflow
-------------------------------------

* **Class**: :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.scf``
* **Workflow type**: Basic
* **Aim**: Manage FLEUR SCF convergence
* **Computational demand**: Corresponding to several ``FleurCalculation``
* **Database footprint**: Output node with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes
* **File repository footprint**: no addition to the ``CalcJob`` run

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.scf import FleurScfWorkChain
    #or
    WorkflowFactory('fleur.scf')

Description/Purpose
^^^^^^^^^^^^^^^^^^^

Converges the charge *density*, the *total energy* or the *largest force* of a given structure,
or stops because the maximum allowed retries are reached.

.. note::

      The workchain is designed to converge only one parameter independently on other parameters.
      Simultaneous convergence of two or three parameters is not implemented to simplify the
      code logic and because one almost always interested in a particular parameter. Moreover,
      it was shown that the total energy tend to converge faster than the charge density.

This workflow manages none or one inpgen calculation and one to several Fleur calculations.
It is one of the most core workflows and often deployed as a sub-workflow.

.. note::
    The FleurScfWorkChain by default determines the calculation resources required for the given system and
    with what hybrid parallelisation to launch Fleur. The resources in the option node given are the maximum
    resources the workflow is allowed to allocate for one simulation (job).
    You can turn off this feature by setting ``determine_resources = False`` in the ``wf_parameters``.

Input nodes
^^^^^^^^^^^

  * ``fleur``: :py:class:`~aiida.orm.Code` - Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen``: :py:class:`~aiida.orm.Code`, optional - Inpgen code using the ``fleur.inpgen``
    plugin
  * ``wf_parameters``: :py:class:`~aiida.orm.Dict`, optional - Settings
    of the workflow behavior
  * ``structure``: :py:class:`~aiida.orm.StructureData`, optional: Crystal structure
    data node.
  * ``calc_parameters``: :py:class:`~aiida.orm.Dict`, optional -
    FLAPW parameters, used by inpgen
  * ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, optional: Fleur input data
    object representing the FLEUR input files
  * ``remote_data``: :py:class:`~aiida.orm.RemoteData`, optional - The remote folder of
    the previous calculation
  * ``options``: :py:class:`~aiida.orm.Dict`, optional - AiiDA options
    (queues, cpus)
  * ``settings``: :py:class:`~aiida.orm.Dict`, optional - special settings
    for Fleur calculations.


As you can see the SCF workchain has a lot of optional inputs. However, it does not mean all of
them can be left unspecified. You must to specify a pre-defined minimal set of inputs. The possible
sets can be found below in the Layout section.

Returns nodes
^^^^^^^^^^^^^

  * ``output_scf_wc_para``: :py:class:`~aiida.orm.Dict` -  Main results of the workflow
  * ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` - An inp.xml that was
    actually used.
  * ``last_fleur_calc_output``: :py:class:`~aiida.orm.Dict` - Output node
    of the last Fleur calculation.

Default inputs
^^^^^^^^^^^^^^
All possible workflow parameters and their defaults.

.. code-block:: python

    _wf_default = {'fleur_runmax': 4,                 # Maximum number of fleur jobs/starts
                   'density_converged': 0.00002,      # Stop if charge density is converged below this value
                   'energy_converged': 0.002,         # Stop if total energy is converged below this value
                   'force_converged': 0.002,          # Stop if the largest force is converged below this value
                   'mode': 'density',                 # which parameter to converge: 'density', 'force' or 'energy'
                   'serial': False,                   # execute fleur with mpi or without
                   'itmax_per_run': 30,               # Maximum iterations run for one Fleur job
                   'force_dict': {'qfix': 2,          # parameters required for the 'force' mode
                                  'forcealpha': 0.5,
                                  'forcemix': 2},
                   'inpxml_changes': [],              # (expert) List of further changes applied to the inp.xml after the inpgen run
                  }                                   # tuples (function_name, [parameters]), have to be the function names supported by fleurinpmodifier

.. note::

  Only one of ``density_converged``, ``energy_converged`` or ``force_converged``
  is used by the workchain that corresponds to the 'mode'. The other two are ignored.

Layout
^^^^^^

Similarly to :py:class:`~aiida_fleur.calculation.fleur.FleurCalculation`, SCF workchain has several
input combinations that implicitly define the workchain layout. Depending
on the setup of the inputs, one of four supported scenarios will happen:

1. **fleurinp**:

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation.

2. **fleurinp** + **remote_data** (FLEUR):

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Moreover, initial charge density will be
      copied from the folder of the remote folder.

3. **remote_data** (FLEUR):

      inp.xml file and initial
      charge density will be copied from the remote folder.

4. **structure**:

      inpgen code will be used to generate a new **fleurinp** using a given structure.
      Generated **fleurinp** will be used as input for the first FLEUR calculation.


For example, if you want to continue converging a charge density, use the option 3.
If you want to change
something in the inp.xml and use the old charge density you should use option 2. To do this, you can
retrieve a FleurinpData produced by the parent calculation and change it via FleurinpModifier,
use it as an input together with the RemoteFolder.

The general layout does not depend on the scenario, SCF workchain sequentially submits several
FLEUR calculation to achieve a convergence criterion.

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
