.. _ssdisp_wc:

Fleur Spin-Spiral Dispersion workchain
--------------------------------------

* **Current version**: 0.1.0
* **Class**: :py:class:`~aiida_fleur.workflows.ssdisp.FleurSSDispWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.ssdisp``
* **Workflow type**: Scientific workchain, force-theorem subgroup
* **Aim**: Calculate spin-spiral energy dispersion over given q-points.
* **Computational demand**: 1 :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain` and
  1 :py:class:`~aiida_fleur.calculation.fleur.FleurCalculation`
* **Database footprint**: Outputnode with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes
* **File repository footprint**: no addition to the ``JobCalculations`` run

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.ssdisp import FleurSSDispWorkChain
    #or
    WorkflowFactory('fleur.ssdisp')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
This workchain calculates spin spiral energy  dispersion over a given set of q-points.
Resulting energies do not contain terms, corresponding to DMI energies. To take into account DMI,
see the FleurDMIWorkChain documentation.

In this workchain the force-theorem is employed which means the workchain converges
a reference charge density first
then it submits a single FleurCalculation with a ``<forceTheorem>`` tag. However, it is possible
to specify inputs to use external pre-converged charge density and use is as a reference.

Input nodes
^^^^^^^^^^^

  * ``fleur``: :py:class:`~aiida.orm.Code` - Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen``, optional: :py:class:`~aiida.orm.Code` - Inpgen code using the ``fleur.inpgen``
    plugin
  * ``wf_parameters``: :py:class:`~aiida.orm.Dict`, optional - Settings
    of the workflow behavior
  * ``structure``: :py:class:`~aiida.orm.StructureData`, optional: Crystal structure
    data node.
  * ``calc_parameters``: :py:class:`~aiida.orm.Dict`, optional -
    FLAPW parameters, used by inpgen
  * ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, optional: Fleur input data
    object representing the fleur input files
  * ``remote_data``: :py:class:`~aiida.orm.RemoteData`, optional - The remote folder of
    the previous calculation
  * ``options``: :py:class:`~aiida.orm.Dict`, optional - AiiDA options
    (queues, cpus)

Returns nodes
^^^^^^^^^^^^^

  * ``out``: :py:class:`~aiida.orm.Dict` -  Information of
    workflow results like success, last result node, list with convergence behavior

Default inputs
^^^^^^^^^^^^^^
Workflow parameters and their defaults:

.. code-block:: python

    wf_parameters_dict = {
        'fleur_runmax': 10,                         # needed for SCF
        'density_converged' : 0.00005,              # needed for SCF
        'serial' : False,                           # needed for SCF
        'itmax_per_run' : 30,                       # needed for SCF
        'beta' : {'all' : 1.57079},                 # see description below
        'alpha_mix' : 0.015,                        # sets mixing parameter alpha
        'prop_dir' : [1.0, 0.0, 0.0],               # sets a propagation direction of a q-vector
        'q_vectors': ['0.0 0.0 0.0',                # set a set of q-vectors to calculate SSDispersion
                      '0.125 0.0 0.0',
                      '0.250 0.0 0.0',
                      '0.375 0.0 0.0'],
        'ref_qss' : '0.0 0.0 0.0',                  # sets a q-vector for the reference calculation
        'input_converged' : False,                  # True, if charge density from remote folder has to be converged
        'inpxml_changes' : []                       # needed for SCF
        }

Workchain parameters contain a set of parameters needed by the SCF workchain.
There are also SSDisp-specific parameters such as ``beta``, ``alpha-mix``, ``prop_dir``,
``q_vectors``, ``ref_qss`` and ``input_converged``.

``beta`` is a python dictionary containing a key: value pairs. Each pair sets ``beta`` parameter
in an inp.xml file. Key string corresponds to the atom label, if key equals `all` then all atoms
will be changed. For example,

.. code-block:: python

    'beta' : {'222' : 1.57079}

changes

.. code-block:: html

      <atomGroup species="Fe-1">
         <filmPos label="                 222">.0000000000 .0000000000 -11.4075100502</filmPos>
         <force calculate="T" relaxXYZ="TTT"/>
         <nocoParams l_relax="F" alpha=".00000000" beta="0.00000" b_cons_x=".00000000" b_cons_y=".00000000"/>
      </atomGroup>

to:

.. code-block:: html

      <atomGroup species="Fe-1">
         <filmPos label="                 222">.0000000000 .0000000000 -11.4075100502</filmPos>
         <force calculate="T" relaxXYZ="TTT"/>
         <nocoParams l_relax="F" alpha=".00000000" beta="1.57079" b_cons_x=".00000000" b_cons_y=".00000000"/>
      </atomGroup>

``prop_dir`` is used only if inpgen must be run (structure node given in the inputs). This
value is passed to `calc_parameters['qss']` and written into the input for inpgen. Thus it shows
the intention of a user on what kind of q-mesh he/she wants to use to properly set up
symmetry operations in the reference calculation.

``input_converged`` is used only if a ``remote_date`` node is given in the input. Is has to be set
True if there is no need to converge a given charge density and it can be used directly for the
force-theorem step. If it is set to False, input charge density will be submitted into scf
workchain before the force-theorem step to achieve the convergence.

Layout
^^^^^^
SSDisp workchain has several
input combinations that implicitly define the workchain layout. Depending
on the setup of the inputs, one of four supported scenarios will happen:

1. **fleurinp**:

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Submits SCF workchain to obtain the reference charge density, then
      makes a force-theorem FLEUR calculation.

      Workchain parameters that are used:

        #. SCF-related parameters
        #. beta
        #. alpha_mix
        #. prop_dir
        #. q_vectors
        #. inpxml_changes

      The other are ignored.

2. **fleurinp** + **parent_folder** (FLEUR):

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Moreover, initial charge density will be
      copied from the folder of the parent calculation. If ``input_converged`` set to False,
      first submits a SCF workchain to converge given charge density further; directly submits
      a force-theorem calculation otherwise.


3. **parent_folder** (FLEUR):

      inp.xml file and initial
      charge density will be copied from the folder of the parent FLEUR calculation.
      If ``input_converged`` set to False, first
      submits a SCF workchain to converge given charge density further; directly submits
      a force-theorem calculation otherwise.

4. **structure**:

      Submits inpgen calculation to generate a new **fleurinp** using a given structure which
      is followed by the SCF workchain to obtain the reference charge density. Submits a
      force-theorem FLEUR calculation after.


Example usage
^^^^^^^^^^^^^
Still has to be documented

Output node example
^^^^^^^^^^^^^^^^^^^
Still has to be documented

Error handling
^^^^^^^^^^^^^^
Still has to be documented
