.. _using_workflows:

Using the AiiDA-FLEUR WorkChains
================================

.. contents::
   :local:

This page describes the contract that **every** AiiDA-FLEUR workchain obeys: how you point it at a
starting structure, how you steer its physics, how you give it compute resources, how you change
``inp.xml``, and how you read its results. The page for an individual workchain documents only what
is specific to it.

Everything below is the state as of aiida-fleur 3.0.0. Where a workchain deviates from the common
rule, the deviation is listed explicitly rather than glossed over.

Choosing a workchain
++++++++++++++++++++

All workchains are registered as AiiDA entry points and are loaded with
:py:func:`~aiida.plugins.WorkflowFactory`::

    from aiida.plugins import WorkflowFactory

    FleurScfWorkChain = WorkflowFactory('fleur.scf')

The "Start from" column uses the vocabulary explained in `The three starting points`_; ``scf`` means
the exposed sub-workchain namespace of that name.

.. list-table::
   :header-rows: 1
   :widths: 16 22 30 20 12

   * - Entry point
     - Class
     - Computes
     - Start from
     - Details
   * - ``fleur.scf``
     - ``FleurScfWorkChain``
     - Converges the charge density, total energy or largest force. The workhorse every other
       workchain builds on.
     - ``structure``, ``fleurinp`` or ``remote_data``
     - :ref:`scf_wc`
   * - ``fleur.base``
     - ``FleurBaseWorkChain``
     - A single FLEUR run with automated error handling and restarts.
     - ``fleurinp`` (+ ``parent_folder``)
     - :ref:`base_wc`
   * - ``fleur.base_relax``
     - ``FleurBaseRelaxWorkChain``
     - ``fleur.relax`` with automated error handling and restarts.
     - exposed ``relax`` inputs
     - :ref:`base_relax_wc`
   * - ``fleur.relax``
     - ``FleurRelaxWorkChain``
     - Structure optimization (atomic forces).
     - ``scf``
     - :ref:`relax_wc`
   * - ``fleur.relax_torque``
     - ``FleurRelaxTorqueWorkChain``
     - Spin-structure optimization (magnetic torques).
     - ``scf``
     - API reference only
   * - ``fleur.eos``
     - ``FleurEosWorkChain``
     - Equation of states; Birch-Murnaghan fit for bulk modulus and groundstate volume.
     - ``structure`` or ``fleurinp``
     - :ref:`eos_wc`
   * - ``fleur.strain``
     - ``FleurStrainWorkChain``
     - Deformation potential ``d(Eg)/d(ln V)``.
     - ``structure`` (required)
     - API reference only
   * - ``fleur.banddos``
     - ``FleurBandDosWorkChain``
     - Band structure or density of states.
     - ``scf`` **or** ``remote_data``
     - :ref:`dos_band_wc`
   * - ``fleur.orbcontrol``
     - ``FleurOrbControlWorkChain``
     - Groundstate density matrix of a DFT+U calculation.
     - ``scf_no_ldau``, ``remote_data``, ``fleurinp``, ``structure`` or ``fixed_remotes``
     - :ref:`orbcontrol_wc`
   * - ``fleur.cfcoeff``
     - ``FleurCFCoeffWorkChain``
     - Rare-earth crystal field coefficients.
     - ``scf`` **or** ``orbcontrol``
     - :ref:`cfcoeff_wc`
   * - ``fleur.jij``
     - ``FleurJijWorkChain``
     - Full Jij tensor from three SOC Green's-function calculations (z, x, y).
     - ``scf``, ``remote_data`` or ``greensf_*`` files
     - API reference only
   * - ``fleur.mae``
     - ``FleurMaeWorkChain``
     - Magnetic anisotropy energy, force-theorem.
     - ``scf`` **or** ``remote_data``
     - :ref:`mae_wc`
   * - ``fleur.mae_conv``
     - ``FleurMaeConvWorkChain``
     - Magnetic anisotropy energy, one self-consistent run per SQA.
     - ``scf``
     - :ref:`mae_conv_wc`
   * - ``fleur.ssdisp``
     - ``FleurSSDispWorkChain``
     - Spin-spiral dispersion, force-theorem.
     - ``scf`` **or** ``remote_data``
     - :ref:`ssdisp_wc`
   * - ``fleur.ssdisp_conv``
     - ``FleurSSDispConvWorkChain``
     - Spin-spiral dispersion, one self-consistent run per q-vector.
     - ``scf``
     - :ref:`ssdisp_conv_wc`
   * - ``fleur.dmi``
     - ``FleurDMIWorkChain``
     - Dzyaloshinskii-Moriya energy dispersion, force-theorem.
     - ``scf`` **or** ``remote_data``
     - :ref:`dmi_wc`
   * - ``fleur.fsm``
     - ``FleurFsmWorkChain``
     - Fixed spin moment calculations over a list of moments.
     - ``scf`` (with ``scf.structure``)
     - API reference only
   * - ``fleur.cutoff_conv``
     - ``FleurCutoffConvWorkChain``
     - Sequential ``Kmax``, k-point and smearing convergence.
     - ``structure`` (required)
     - API reference only
   * - ``fleur.init_cls``
     - ``FleurInitialCLSWorkChain``
     - Initial-state core level shifts against elemental references.
     - ``structure`` or ``fleurinp``
     - :ref:`init_cl_wc`
   * - ``fleur.corehole``
     - ``FleurCoreholeWorkChain``
     - Core-hole binding energies from total-energy differences on supercells.
     - ``structure`` or ``fleurinp``
     - :ref:`corehole_wc`
   * - ``fleur.create_magnetic``
     - ``FleurCreateMagneticWorkChain``
     - Builds a relaxed magnetic film on a substrate (returns a structure, not energies).
     - ``eos``, ``relax`` or ``optimized_structure``
     - :ref:`create_magnetic_wc`

"API reference only" means the workchain has no dedicated page yet; its ports and ``wf_parameters``
defaults are documented in its docstrings, reachable from :ref:`the module reference <code_wc>`,
and discoverable as described in `Discovering the defaults`_.

The three starting points
+++++++++++++++++++++++++

A workchain is told what to compute on through exactly three port names. There are no synonyms —
if you are looking for ``remote``, ``parent_folder`` or ``structure_data``, they do not exist at
this level.

``structure``
    A :py:class:`~aiida.orm.StructureData`, optionally with ``calc_parameters``
    (:py:class:`~aiida.orm.Dict`) carrying the FLAPW parameters. The workchain generates the FLEUR
    input itself.

``fleurinp``
    A ready :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, i.e. a complete ``inp.xml``.
    Nothing is generated; what you provide is what runs (modulo ``inpxml_changes``).

``remote_data``
    A :py:class:`~aiida.orm.RemoteData` from a previous FLEUR run. The charge density and
    ``inp.xml`` of that calculation are reused, which is how you continue from a converged
    groundstate without recomputing it.

.. note::

    Since 3.0.0 input generation runs **in-process** through ``pyfleur`` — there is no ``inpgen``
    CalcJob any more. The ``inpgen``, ``options_inpgen`` and ``settings_inpgen`` ports that some
    workchains still declare are ``non_db`` and ignored; they exist only so that older submission
    scripts keep running, and will be removed in the next major release. Passing a code node there
    has no effect and is not recorded in the provenance graph.

Which combination is legal
--------------------------

For ``FleurBandDosWorkChain``, ``FleurMaeWorkChain``, ``FleurSSDispWorkChain`` and
``FleurDMIWorkChain`` the rule is enforced by a shared
:py:func:`~aiida_fleur.tools.common_fleur_wf.validate_fleur_entry_points` wired in as
``spec.inputs.validator``:

    Give **either** the ``scf`` namespace (to converge a new groundstate first) **or** a
    ``remote_data`` to continue from — optionally overlaid with a ``fleurinp``. Not both, and not
    neither.

Because it is a spec validator, an illegal combination is rejected **at submission time** with a
plain error message, instead of creating a process node that immediately aborts.

``FleurJijWorkChain`` and ``FleurOrbControlWorkChain`` follow the same idea but have extra entry
points (Jij can postprocess existing ``greensf_*`` files; OrbControl accepts ``fixed_remotes`` /
``relaxed_remotes``), so they validate in their first step and return exit code ``231`` instead.
The remaining workchains also check in their first step.

Steering the physics: ``wf_parameters``
+++++++++++++++++++++++++++++++++++++++

Every workchain that has any physics to steer takes an optional ``wf_parameters``
:py:class:`~aiida.orm.Dict`. What you give is merged onto the class attribute ``_default_wf_para``,
so you only supply the keys you want to change.

Unknown keys are an error
-------------------------

A key that the workchain defines no default for is rejected with exit code ``230``
(``ERROR_INVALID_INPUT_PARAM``). This catches typos instead of silently ignoring them.

.. warning::

    Three workchains do **not** do this yet and will silently ignore an unknown key:
    ``FleurStrainWorkChain``, ``FleurCoreholeWorkChain`` and ``FleurInitialCLSWorkChain``. Check
    your spelling carefully when using those three. Do not rely on this behaviour — it is
    considered a defect, not a feature.

Two merge semantics
-------------------

For a key whose default is itself a dictionary, there are two behaviours, and which one you get
depends on the workchain:

**Key-by-key (nested)** — ``fleur.scf``, ``fleur.jij``, ``fleur.corehole``. Sub-keys you do not
mention keep their default.

**Wholesale replacement** — every other workchain. Your sub-dict *replaces* the default entirely.

The practical consequence, using ``add_comp_para``::

    # FleurScfWorkChain (nested): only_even_MPI is changed, the other three keep their defaults
    # -> {'only_even_MPI': True, 'forbid_single_mpi': False,
    #     'max_queue_nodes': 20, 'max_queue_wallclock_sec': 86400}
    Dict({'add_comp_para': {'only_even_MPI': True}})

    # FleurMaeWorkChain (wholesale): the other three sub-keys are GONE
    # -> {'only_even_MPI': True}
    Dict({'add_comp_para': {'only_even_MPI': True}})

This split is deliberate. Keys such as ``beta``, ``sqas``, ``q_vectors``, ``references`` and
``replacements`` are open-ended maps keyed by atom or q-point label; merging defaults into them
would silently add entries you never asked for. When in doubt, **spell out every sub-key you care
about** — that is correct under both semantics.

Discovering the defaults
------------------------

The defaults are a plain class attribute, so you can always print them::

    from aiida.plugins import WorkflowFactory

    print(WorkflowFactory('fleur.scf')._default_wf_para)
    print(WorkflowFactory('fleur.mae')._default_options)

This is the authoritative answer for any workchain, including the ones without a dedicated
documentation page.

Compute resources: ``options``
++++++++++++++++++++++++++++++

``options`` is a :py:class:`~aiida.orm.Dict` holding the AiiDA scheduler options — resources, queue
name, wallclock limit — and is merged onto the class attribute ``_default_options`` the same way.

.. code-block:: python

    options = Dict({
        'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4},
        'max_wallclock_seconds': 6 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
    })

Beyond the standard AiiDA keys, ``optimize_resources`` (default ``True``) controls whether
``FleurBaseWorkChain`` re-factorises your MPI/OpenMP layout against the k-point count before
submitting; see :ref:`base_wc`.

**Where to put it is the single most common mistake.** Workchains fall into two groups:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Group
     - Workchains
   * - Has its own top-level ``options``
     - ``fleur.base`` (**required**, no default), ``fleur.scf``, ``fleur.banddos``, ``fleur.mae``,
       ``fleur.ssdisp``, ``fleur.dmi``, ``fleur.jij``, ``fleur.orbcontrol``, ``fleur.corehole``,
       ``fleur.init_cls``, ``fleur.strain``
   * - No ``options`` port at all — resources come **only** from the exposed sub-namespace
     - ``fleur.eos``, ``fleur.relax``, ``fleur.relax_torque``, ``fleur.base_relax``,
       ``fleur.mae_conv``, ``fleur.ssdisp_conv``, ``fleur.cfcoeff``, ``fleur.fsm``,
       ``fleur.cutoff_conv``, ``fleur.create_magnetic``

So for an EOS run the resources go in ``inputs['scf']['options']``; there is no
``inputs['options']`` and passing one is a validation error.

.. note::

    ``fleur.banddos``, ``fleur.mae``, ``fleur.ssdisp``, ``fleur.dmi``, ``fleur.jij`` and
    ``fleur.orbcontrol`` are hybrids: they have **both**. The top-level ``options`` sizes the final
    force-theorem / banddos / fixed-density-matrix calculation, while ``scf.options`` sizes the
    preceding SCF. Setting only one of the two leaves the other at its class default.

Changing ``inp.xml``: ``inpxml_changes``
++++++++++++++++++++++++++++++++++++++++

A stored ``FleurinpData`` is immutable, so a workchain cannot edit it in place. Instead you record
a **task list** of modifications, which the workchain replays inside the
``modify_fleurinpdata`` calcfunction to produce a *new* ``FleurinpData`` — so the change is part of
the provenance graph.

The task list lives under the ``inpxml_changes`` key of ``wf_parameters`` and is a list of
``(method_name, kwargs_dict)`` tuples. The kwargs are passed **by keyword** to the
:py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` method of that name, so the key
names must match that method's signature::

    inpxml_changes = [
        ('set_inpchanges', {'changes': {'l_noco': False}}),
        ('set_species', {'species_name': 'Fe-1', 'attributedict': {'mtSphere': {'radius': 2.2}}}),
    ]

The preferred way to build the list is the ``inpxml_changes`` context manager, which gets the
keyword names right for you and writes the result into the right place::

    from aiida_fleur.data.fleurinpmodifier import inpxml_changes

    inputs = FleurEosWorkChain.get_builder()

    # write into the sub-workchain's wf_parameters, not the top level
    with inpxml_changes(inputs.scf) as fm:
        fm.set_inpchanges({'l_noco': False})
        fm.set_species('Fe-1', {'mtSphere': {'radius': 2.2}})

Passing the builder root (``with inpxml_changes(inputs) as fm:``) targets the top-level
``wf_parameters`` instead. A plain dict or an unstored :py:class:`~aiida.orm.Dict` also works; an
already-stored ``Dict`` raises ``ValueError``, because modifying it would rewrite existing
provenance.

For the full list of available modification methods see :ref:`fleurinp_mod`.

Which workchains accept it
--------------------------

``inpxml_changes`` is a ``wf_parameters`` key of ``fleur.scf``, ``fleur.banddos``, ``fleur.mae``,
``fleur.ssdisp``, ``fleur.dmi``, ``fleur.jij``, ``fleur.orbcontrol`` and ``fleur.strain`` (which
forwards it verbatim to its sub-SCF).

It is **not** a key of ``fleur.eos``, ``fleur.cutoff_conv``, ``fleur.fsm``, ``fleur.init_cls``,
``fleur.mae_conv``, ``fleur.ssdisp_conv``, ``fleur.cfcoeff``, ``fleur.corehole`` or
``fleur.create_magnetic`` — for those, put the changes in the **sub-workchain's** namespace, as in
the ``inputs.scf`` example above. ``fleur.relax`` and ``fleur.relax_torque`` actively rewrite their
sub-SCF's list (they add and later strip their own ``shift_value`` tasks), so pass yours through
``scf.wf_parameters`` there too.

Nested namespaces
+++++++++++++++++

A workchain pulls in the inputs of the workchain it drives with ``spec.expose_inputs(...,
namespace='scf')``. The namespace name is part of the public API: you write a nested dict with that
key.

A complete EOS example
----------------------

``FleurEosWorkChain`` exposes ``FleurScfWorkChain`` under ``scf``, excluding the three starting-point
ports (which EOS supplies itself, once per volume)::

    from aiida import orm
    from aiida.engine import submit
    from aiida.plugins import WorkflowFactory

    FleurEosWorkChain = WorkflowFactory('fleur.eos')

    inputs = {
        'structure': structure,                        # or 'fleurinp': fleurinp
        'wf_parameters': orm.Dict({
            'points': 9,
            'step': 0.005,
            'guess': 1.00,
            'enforce_same_para': True,
        }),
        'scf': {
            'fleur': fleur_code,                       # required
            'wf_parameters': orm.Dict({
                'fleur_runmax': 4,
                'density_converged': 0.001,
                'itmax_per_run': 50,
            }),
            'calc_parameters': orm.Dict({'atom': {'element': 'Si', 'rmt': 2.1}}),
            'options': orm.Dict({
                'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4},
                'max_wallclock_seconds': 6 * 60 * 60,
            }),
        },
    }

    node = submit(FleurEosWorkChain, **inputs)

That is the whole nesting — **two** levels. ``FleurScfWorkChain`` does not expose a ``base``
namespace: it assembles the ``FleurBaseWorkChain`` inputs itself in
:py:func:`~aiida_fleur.tools.common_fleur_wf.get_inputs_fleur`, and ``scf.options`` is what
eventually becomes the ``FleurCalculation``'s ``metadata.options``. So ``base`` and ``fleur`` never
appear as namespaces you write.

Note also that ``FleurBaseWorkChain`` inherits CalcJob port naming — ``code`` and ``parent_folder``
rather than ``fleur`` and ``remote_data``. You only meet those names if you drive it directly.

The deepest case
----------------

``FleurCreateMagneticWorkChain`` is the only three-level workchain in the package::

    inputs = {
        'wf_parameters': orm.Dict({...}),
        'eos': {
            'scf': {'fleur': fleur_code, 'options': options, ...},
        },
        'relax': {
            'scf':       {'fleur': fleur_code, 'options': options, ...},
            'final_scf': {'options': options, ...},
            'max_iterations': orm.Int(5),          # a BaseRestartWorkChain port
        },
    }

``FleurBaseRelaxWorkChain`` exposes ``FleurRelaxWorkChain`` with **no** namespace of its own, which
is why the restart wrapper is invisible here and ``relax.scf`` reaches straight through to the SCF.

.. warning::

    There is no automatic type coercion anywhere in aiida-fleur: no port declares
    ``serializer=orm.to_aiida_type``. Every ``Dict`` input must be wrapped by hand. Passing a plain
    Python dictionary raises a validation error at submission.

Reading the results
+++++++++++++++++++

The main result node
--------------------

Every workchain returns exactly one :py:class:`~aiida.orm.Dict` named
``output_<wcname>_wc_para`` holding the physical results::

    node = orm.load_node(<pk>)
    results = node.outputs.output_eos_wc_para.get_dict()

    results['bulk_modulus']          # the physics
    results['workflow_name']         # 'FleurEosWorkChain'
    results['workflow_version']      # matches the class _workflowversion
    results['successful']            # whether the workchain considers the data usable
    results['info'], results['warnings'], results['errors']

The bookkeeping keys are as important as the physics: they are what lets you judge, later, whether
a stored result is trustworthy and which code version produced it.

``FleurCreateMagneticWorkChain`` is the exception — it produces a structure
(``magnetic_structure``), not a result dictionary.

Outputs of the sub-process
--------------------------

Rather than making you walk the provenance graph by pk, a workchain re-exposes the outputs of the
sub-process it ran, under a namespace named after the **role** that sub-process played:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Workchain
     - Namespace
     - Contents
   * - ``fleur.scf``
     - ``last_calc``
     - the final ``FleurBaseWorkChain`` (``last_calc.output_parameters``, ``last_calc.retrieved``)
   * - ``fleur.relax`` / ``fleur.relax_torque``
     - ``last_scf``
     - the final ``FleurScfWorkChain``
   * - ``fleur.banddos``
     - ``banddos_calc``
     - the band/DOS ``FleurBaseWorkChain``
   * - ``fleur.orbcontrol``
     - ``groundstate_scf``
     - the SCF that produced the groundstate density matrix

Some further outputs predate the naming convention and are kept because renaming a link label would
break stored provenance: ``optimized_structure`` (relax), ``magnetic_structure``
(create_magnetic), and Jij's ``jij_tensor_z`` / ``full_jij_tensor`` / ``jij_interactions``. Treat
them as fixed; new workchains do not follow them.

When it fails
+++++++++++++

A finished workchain carries an exit status. Since 3.0.0 the numbers below 400 mean the same thing
in every workchain, so you can branch on them without knowing which workchain produced the node::

    node = orm.load_node(<pk>)
    if node.is_finished_ok:
        ...
    elif node.exit_status == 362:
        print('the SCF cycle did not converge — raise fleur_runmax or loosen density_converged')
    elif node.exit_status == 230:
        print('a wf_parameters key was rejected; check the report:')
        print(node.get_description())

The shared meanings:

=========  ======================================================================
Code       Meaning
=========  ======================================================================
230        The ``wf_parameters`` dict contains an unknown key or an invalid value
231        The combination of input ports given is not legal for this workchain
233        A given ``Code`` node does not use the expected plugin
235        The requested ``inpxml_changes`` could not be applied
236        The modified ``inp.xml`` no longer validates against the FLEUR schema
334        The reference/parent SCF this workchain builds on failed
335        That reference calculation produced no remote folder to restart from
343        Every sub-calculation of a scan failed
344        Some, but not all, sub-calculations of a scan failed
345        A sub-SCF workchain failed
360        In-process input generation (pyfleur) failed
361        A FLEUR calculation failed
362        An SCF cycle did not reach its convergence criterion
=========  ======================================================================

Codes at 346 and above that are not in this list, and everything from 380 up, are specific to one
workchain. Codes below 230 belong to ``aiida-core``. The complete table is at :ref:`exit_codes`.

``verdi process report <pk>`` is the first thing to read on a failure: every workchain writes
progress and error messages there through ``self.report``.

From the command line
+++++++++++++++++++++

For quick runs the plugin ships a CLI::

    $ aiida-fleur launch scf --help
    $ aiida-fleur launch eos -str Si.cif -f fleur@localhost

Commands exist for ``inpgen``, ``fleur``, ``scf``, ``relax``, ``eos``, ``dos``, ``band``,
``init_cls``, ``corehole``, ``mae``, ``create_magnetic``, ``ssdisp_conv`` and ``dmi``. There is no
command for ``jij``, ``cfcoeff``, ``orbcontrol``, ``mae_conv``, ``relax_torque``, ``strain``,
``cutoff_conv``, ``fsm`` or ``base_relax`` — use a submission script for those. See
:doc:`../cmd/cmd_index` for the full CLI reference.
