###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
"""
Pieces shared by the FLEUR workchains.

Every workchain used to carry its own copy of the same few blocks -- merging ``wf_parameters``
onto the class default, merging ``options``, applying ``inpxml_changes``, collecting the results
of a list of sub-SCFs, and shutting down cleanly. The copies had drifted: two incompatible merge
semantics, two different exception types caught around the same call (one of which could never
fire), and four behaviours behind one ``control_end_wc`` name. This module holds one version of
each.

Nothing here is a workchain and nothing is registered as an entry point; the leading underscore
keeps it out of the ``aiida_fleur.workflows`` namespace that maps onto entry points.
"""
from lxml import etree

from aiida.common.exceptions import NotExistent

from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

#: the parallelisation knobs FleurBaseWorkChain understands. Note ``forbid_single_mpi``:
#: base_fleur reads it unguarded, and the per-workchain copies of this dict used to omit it,
#: surviving only because get_inputs_fleur back-filled it on the way through
DEFAULT_ADD_COMP_PARA = {
    'only_even_MPI': False,
    'forbid_single_mpi': False,
    'max_queue_nodes': 20,
    'max_queue_wallclock_sec': 86400,
}

#: scheduler defaults for a workchain that submits FLEUR itself. ``num_mpiprocs_per_machine``
#: is not optional: base_fleur turns off resource optimisation entirely if it is missing
DEFAULT_COMPUTE_OPTIONS = {
    'resources': {
        'num_machines': 1,
        'num_mpiprocs_per_machine': 1
    },
    'max_wallclock_seconds': 6 * 60 * 60,
    'queue_name': '',
    'custom_scheduler_commands': '',
    'import_sys_environment': False,
    'environment_variables': {},
}


def merge_parameter_dicts(given, defaults, nested=True):
    """
    Fill a user-given parameter dict up with the workchain's defaults.

    :param given: what the user passed, may be empty
    :param defaults: the workchain's ``_default_wf_para`` (or ``_default_options``)
    :param nested: if True a dict-valued default is merged key-by-key, so a user supplying only
                   part of e.g. ``add_comp_para`` keeps the other sub-keys. If False the
                   user's sub-dict replaces the default wholesale.

    :returns: a new dict; neither argument is modified
    """
    merged = dict(given)
    for key, val in defaults.items():
        if nested and isinstance(val, dict):
            merged[key] = {**val, **merged.get(key, {})}
        else:
            merged[key] = merged.get(key, val)
    return merged


def unknown_parameter_keys(given, defaults):
    """
    Return the keys of ``given`` that the workchain does not define a default for.

    Only the top level is checked, which is what every workchain did by hand. A caller that
    finds anything here should abort with ``ERROR_INVALID_INPUT_PARAM``.
    """
    return sorted(key for key in given if key not in defaults)


def apply_inpxml_changes(fleurinp, changes, reporter):
    """
    Apply a list of ``inpxml_changes`` tasks to a FleurinpData and validate the result.

    This is the body of every ``change_fleurinp`` step. The copies had drifted -- some caught
    only ``ValueError`` around ``add_task_list`` where the modifier also raises ``TypeError``
    on a malformed task list -- so the widest of the variants is used here.

    :param fleurinp: the FleurinpData to modify
    :param changes: the task list from ``wf_parameters['inpxml_changes']``
    :param reporter: ``self.report``, so the message lands in the workchain report

    :returns: a tuple ``(new_fleurinp, failure)``. On success ``failure`` is None; on failure
              ``new_fleurinp`` is None and ``failure`` is one of the strings ``'changing'`` or
              ``'invalid'``, which the caller maps to ERROR_CHANGING_FLEURINPUT_FAILED or
              ERROR_INVALID_INPUT_FILE respectively.
    """
    fleurmode = FleurinpModifier(fleurinp)

    try:
        fleurmode.add_task_list(changes)
    except (ValueError, TypeError) as exc:
        reporter('ERROR: Changing the inp.xml file failed. Tried to apply inpxml_changes'
                 f', which failed with {exc}. I abort, good luck next time!')
        return None, 'changing'

    return validate_and_freeze(fleurmode, reporter)


def validate_and_freeze(fleurmode, reporter):
    """
    Validate a prepared FleurinpModifier against the FLEUR schema and freeze it.

    This is the tail every ``change_fleurinp`` step ends with, including the workchains that
    build the modifier themselves rather than only replaying a task list (banddos sets the
    k-point list on it, scf sets convergence parameters, jij builds the Green's-function
    contour).

    :param fleurmode: a FleurinpModifier with its tasks already added
    :param reporter: ``self.report``

    :returns: ``(new_fleurinp, failure)`` -- see :py:func:`apply_inpxml_changes`
    """
    try:
        fleurmode.show(display=False, validate=True)
    except etree.DocumentInvalid:
        reporter('ERROR: input, user wanted inp.xml changes did not validate')
        return None, 'invalid'
    except (ValueError, TypeError) as exc:
        reporter('ERROR: input, user wanted inp.xml changes could not be applied.'
                 f'The following error was raised {exc}')
        return None, 'changing'

    return fleurmode.freeze(), None


def collect_scf_results(workchains, reporter):
    """
    Pull the result Dict out of a set of finished sub-SCF workchains.

    A failed sub-SCF is skipped rather than raised on, which is what the per-workchain copies
    intended. Four of them guarded ``calc.outputs.output_scf_wc_para`` with ``except KeyError``,
    but that attribute access raises ``NotExistentAttributeError`` -- an ``AttributeError``, not
    a ``KeyError`` -- so the handler was dead and the workchain aborted instead of skipping.

    :param workchains: mapping of label -> finished sub-workchain node
    :param reporter: ``self.report``

    :returns: ``(results, failed_labels)`` where results maps label -> output Dict node
    """
    results, failed = {}, []
    for label, calc in workchains.items():
        if not calc.is_finished_ok:
            reporter(f'One SCF workflow was not successful: {label}')
            failed.append(label)
            continue
        try:
            results[label] = calc.outputs.output_scf_wc_para
        except NotExistent:
            reporter(f'One SCF workflow failed, no scf output node: {label}. I skip this one.')
            failed.append(label)
    return results, failed
