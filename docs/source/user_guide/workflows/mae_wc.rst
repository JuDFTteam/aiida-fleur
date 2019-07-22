.. _mae_wc:

Fleur Magnetic Anisotropy Energy workflow
-----------------------------------------

* **Class**: :py:class:`~aiida_fleur.workflows.mae.FleurMaeWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.mae``
* **Workflow type**: Scientific workchain, force-theorem subgroup
* **Aim**: Calculate Magnetic Anisotropy Energies along given spin quantization axes
* **Computational demand**: 1 ``Fleur SCF WorkChain`` and 1
  :py:class:`~aiida_fleur.calculation.fleur.FleurCalculation` d
* **Database footprint**: Outputnode with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes
* **File repository footprint**: no addition to the ``JobCalculations`` run

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.mae import FleurMaeWorkChain
    #or
    WorkflowFactory('fleur.mae')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
This workchain calculates Magnetic Anisotropy Energy over a given set of spin-quantization axes.
The force-theorem is employed which means the workchain converges a reference charge density first
then it submits a single FleurCalculation with a `<forceTheorem>` tag.

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

  * ``out`` (*ParameterData*): Information of workflow results like success,
    last result node, list with convergence behavior

Default inputs
^^^^^^^^^^^^^^
Workflow parameters.

.. code-block:: python

    wf_parameters_dict = {
        'sqa_ref': [0.7, 0.7],                      # set SQA for the reference calculation
        'use_soc_ref': False,                       # True, if include SOC terms into the reference calculation
        'input_converged' : False,                  # True, if input charge density is converged
        'fleur_runmax': 10,                         # needed for SCF
        'sqas_theta': [0.0, 1.57079, 1.57079],      # sets SOC theta values
        'sqas_phi': [0.0, 0.0, 1.57079],            # sets SOC phi values
        'alpha_mix': 0.05,                          # sets mixing parameter alpha
        'density_converged': 0.00005,               # needed for SCF
        'serial': False,                            # needed for SCF
        'itmax_per_run': 30,                        # needed for SCF
        'soc_off': [],                              # switches off SOC on a given atom
        'inpxml_changes': [],                       # needed for SCF
    }

Workchain parameters contain a set of parameters needed by the SCF workchain.
There are also DMI-specific parameters such as ``alpha-mix``, ``sqas_theta``, ``sqas_phi``,
``soc_off``, ``input_converged``, ``sqa_ref``, ``use_soc_ref``.

``soc_off`` is a python list containing atoms labels. SOC is switched off for species, corresponding
to the atom with a given label.

.. note::

    It can be that the spice correspond to several atoms and ``soc_off`` switches off SOC for atoms
    that was not intended to change. You must be careful with this. For more information, see the
    LINK.

An example of ``soc_off`` work:

.. code-block:: python

    'soc_off': ['458']

changes

.. code-block:: html

      <species name="Ir-2" element="Ir" atomicNumber="77" coreStates="17" magMom=".00000000" flipSpin="T">
         <mtSphere radius="2.52000000" gridPoints="747" logIncrement=".01800000"/>
         <atomicCutoffs lmax="8" lnonsphr="6"/>
         <energyParameters s="6" p="6" d="5" f="5"/>
         <prodBasis lcutm="4" lcutwf="8" select="4 0 4 2"/>
         <lo type="SCLO" l="1" n="5" eDeriv="0"/>
      </species>
      -----
      <atomGroup species="Ir-2">
         <filmPos label="                 458">1.000/4.000 1.000/2.000 11.4074000502</filmPos>
         <force calculate="T" relaxXYZ="TTT"/>
         <nocoParams l_relax="F" alpha=".00000000" beta=".00000000" b_cons_x=".00000000" b_cons_y=".00000000"/>
      </atomGroup>

to:

.. code-block:: html

      <species name="Ir-2" element="Ir" atomicNumber="77" coreStates="17" magMom=".00000000" flipSpin="T">
         <mtSphere radius="2.52000000" gridPoints="747" logIncrement=".01800000"/>
         <atomicCutoffs lmax="8" lnonsphr="6"/>
         <energyParameters s="6" p="6" d="5" f="5"/>
         <prodBasis lcutm="4" lcutwf="8" select="4 0 4 2"/>
         <special socscale="0.0"/>
         <lo type="SCLO" l="1" n="5" eDeriv="0"/>
      </species>

As you can see, I was careful about "Ir-2" specie  and it contained a single atom with a
label 458.

.. _Fleur forceTheorem documentation: https://www.flapw.de/site/xml-advanced/#magnetic-anisotropy-energy-mae

``sqas_theta`` and ``sqas_phi`` are python lists that set SOC theta and phi values. For detailed
explanation see `Fleur forceTheorem documentation`_.

``sqa_ref`` sets a spin quantization axis [theta, phi] for the reference calculation if SOC terms
are switched on by ``use_soc_ref``.

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
        #. sqas_theta
        #. sqas_phi
        #. soc_off
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
