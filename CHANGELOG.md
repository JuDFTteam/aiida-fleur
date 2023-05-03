# Changelog

## v.2.0.0
First release with official support for AiiDA version 2.0. Support for AiiDA 1.X is only
available with releases from the 1.X series of aiida-fleur. Dropped python 3.7 support.
Added support for python 3.11.

### Breaking changes
- The entries `last_calc_uuid` from output dictionary of `FleurSCFWorkChain` and `last_scf_wc_uuid` from `FleurRelaxWorkChain` are removed. Reasoning for this is that having UUIDs in the output dictionary makes it impossible to take advantage of AiiDA's caching mechanism. Both workchains expose the relevant outputs of the under the namespaces `last_calc` and `last_scf` respectively
- Several input/output port changes:
  - `FleurBandDOSworkChain`: Removed `last_calc_retrieved`, replaced with namespace `banddos_calc`
  - `FleurBaseWorkChain`: Removed `final_calc_uuid`
  - Adjusted name of output dictionary to the naming schema `output_<wc_abbrev>_wc_para`: `FleurDMIWorkChain`, `FleurMAEConvWorkChain`, `FleurSSDispWorkChain`, `FleurSSDicpConvWorkChain`
  - `FleurSCFWorkChain`: Removed `last_fleur_calc_output`. Is available under `last_calc.output_parameters`
  - Ports for generic `FleurinpData` are renamed to consistently be `fleurinp`. Affects `FleurCalculation`, `FleurinputgenCalculation`, `FleurBaseWorkChain`

### Expired Deprecations
- `FleurinpModifier`: Removed compatibility with old method names/behaviour before introducing `masci-tools`
- `FleurinpData`: Removed `get_tag`. Use `load_inpxml` and any evaluation routine afterwards instead
- Coordinate conversion functions `abs_to_rel`, etc., These are available in `masci-tools`
- Removed `constants` module. Now only available in `masci-tools`


### Improvements
- New workchain `FleurRelaxTorqueWorkChain` for relaxing non-collinear magnetic configurations
- Fixes in DFT+U handling
  - `FleurCalculation`: added `fleurinp_nmmpmat_priority` key to `settings` to control from where to take the `n_mmp_mat` file if it's in the fleurinp and parent_folder input
  - Fixed several errors in orbcontrol workchain when handling non-converged/failed calculation
  - Added inputs to orbcontrol to restart from intermediate charge densities
- Added `inpxml_changes` contextmanager for easier creation of the workflow parameters input of the same name
```python
from aiida_fleur.data import inpxml_changes

wf_parameters = {}

with inpxml_changes(wf_parameters) as fm:
  fm.set_inpchanges({'kmax': 4, 'itmax': 100})
  fm.set_species('all', {'mtsphere': {'radius': 3}})

print(wf_parameters['inpxml_changes']) #now contains the list like before
```



## v.1.3.1
### release compatible with AiiDA-core 1.3.0+
- Fix for masci-tools dependency constraint. The constraint would previously reject the next minor version of masci-tools (i.e `0.10.0`)
- Small fixes in zenodo metadata
- Added `convert_inpxml` method to `FleurinpData` to convert to different file versions

## v.1.3.0
### release compatible with AiiDA-core 1.3.0+
- Guraranteed support for Fleur versions up to Max6
- Dropped support for python 3.6
- Added CFCoeff Workchain for calculating 4f crystal field coefficients
- General Improvements of Forcetheorem workchains, allow switching kpoints for force theorem calculations
- General Improvements of Orbcontrol workchain, allow starting from structure/charge density without SCF workchain
- Added support for inpgen profiles
- Refactored BaseFleurWorkChain; switched implementation of BaseRestartWorkChain from aiida-fleur to implementation provided by aiida-core
- Added support for starting SCF Workchain with first calculation using straight mixing either for the charge density or the DTF+U density matrix

## v.1.2.1
### release compatible with AiiDA-core 1.3.0+
- General improvements for CreateMagnetic workchain and related methods
- Added OrbControl workchain
- FleurBandDosWorkchain provides AiiDA BandsData for bandstructure calculations and XyData for DOS calculations as outputs
- General Improvements to plot_fleur function, e.g. can now visualize FleurBandDosWorkChain

## v.1.2.0
### release compatible with AiiDA-core 1.3.0+
possibly ready for aiida-core 2.0.0
- supports Fleur MaXR4 and MaXR5 versions with new inpgen
MaXR4 requires providing versions in the code nodes
- Some features relying on the id in the inpgen files,
may be broken by the new inpgen interface change when using MaXR5.1
- Added support for GW calculations with Spex, and the Strain workchain
- Major code refactoring, moving all xml tools to masci-tools (therefore requires masci-tools >=0.4.8)
- Also all file parsers are overworked and moved to masci-tools
- Work over of the BanddosWorkChain.
- FleurinpData now consistently supports more included xml files (kpts.xml, sym.xml, ...)
- Added new modification functions to the FleurinpModifier for kpoint manipulation for Max5


## v.1.1.4
### release compatible with AiiDA-core 1.3.0
- still support of Fleur MaXR4 version with inpgen
- Does not support yet Fleur MaXR5 and new inpgen
- Fixed numpy dependency issue with aiida-common-workflows and quantum mobile

## v1.1.3
### release compatible with AiiDA-core 1.3.0
- still support of Fleur MaXR4 version with inpgen
- Does not support yet for Fleur MaXR5 and new inpgen
- Set_kpoints was moved from fleurinp to fleurinpmodifier
- Break_symmetry of a structure was refactored
- Implemented feature in fleurinputCalculation to set significant figures
- Implemented feature scf can now use default queues specified in code extras
- First implementation of relax type None, which cases the relax workchain to skip the
relaxation, becoming a usual scf wc,  which might make it easier to switch relaxation on
and off in other workchains.
- Fleur parser parses now the total magnetic moment of the cell
- Introduced common constants, for bohr and htr, increased precision
- Command line interface (CLI) `aiida-fleur` with various functionalities exposed
- For devs: Increased test coverage, codecov is now added to CI and linked to badge
removed some older outdated code

## v1.1.2
### release compatible with AiiDA-core 1.3.0
- still support of Fleur MaX4 version (release branch) with inpgen
- downdgraded aiida-core dependency, do release does not depend on aiida-testing
- Added userfriendly LDA+U support
- SCF workchain can generate kpoints from a given density
- Base fleur has now time limit error handler
- Relax workchain can now run a final scf
- Update documentation for corehole, initial CLS and create magnetic workchains
- Various bug fixes and robustness improvements of magnetic workchains
- For devs: Enforced pre-commit, tests dir moved out of source

## v1.1.1
### release compatible with AiiDA-core 1.4.0
- still support of Fleur MaX4 version (release branch) with inpgen
- bugfixes and other general improvements
- new: BandDos workchain: workchain for Band and DOS calculation using the new Fleur BandDOS file
- basic workchains are now cachable, by moving cf out of workchains
- first calcjob and workchain regression tests for outside CI env
- provenance of the result nodes of magnetic workchains is fixed
- corehole and initial_cls workchain are fixed and working
- exit codes for inpgen parser

## v1.1.0
### release compatible with AiiDA-core 1.1.0
- support of Fleur Max4 version (release branch)
- make use of namespaces for nested workchains
- inputs for the workchains are checked more strictly
- exit codes are organised and consistent
- FleurRestart workchain: automatic parallelisation is able to make OMP threading
- new: BaseRelax workchain wrapping RelaxWorkChain and fixes its failures
- new: CreateMagnetic workchain that creates relaxed film structure
- increased unit test coverage for tools and utilities
- code clean-ups, pylint score increased to 7.49

## v1.0.0a
### release compatible with AiiDA-core 1.0.0b5
- added magnetic workchains
- added geometry optimisation (relax) workchain
- implemented the use of exit codes
- added FLEUR restart workchain
- integrated new Fleur input schema files
- other improvements of the workchains and calculations
- code clean-ups, documentation updates

## v0.6.0
### release for MaX virtual machine, not so well testet, but used in production mode. some things are currently half done
- added CI
- added basic tests, coverage still bad, but tests if plugin is installed right
- added MANIFEST
- fixed fleur_schema isssued if installed as python package (with manifest)
- integrated the new Fleur schema files
- bunch of new utiltity
- advancements of workflows
- correction of AiiDA graphs of most workchains, Quick and dirt, still unclear what is the right way to do these things, aiida_core still changes
- increased pylint score from 0 to >5

## v0.5.0
### Merge with advanced workflow repo
- this included the corehole and inital corehole workflow as well calculation of formation energies
  Therefore this is the first public released verison of them with in MaX
- all the utility of the corelevel repo is now under aiida_fleur/tools


## v0.4.0
- further improvment of scf, eos and other workchains
- a workchain delta form calculation a delta value, or performing calculation on the delta structures or a group of structures in a single shot
- lots of new utilty methods for structure dealings, fleur parameters and so on
- lots of bugfixes
- new system for the schema files, user does not has to add aiida-fleur to pythonpath or hack the schema paths.
- added new tests, submission tests and standard fleur tests
- first documention online, still very rusty still some issues there (stay with local one)

## v0.3.0

### Merge with workflows repo
- the second repository with basic workflows was merged into the plugin repostitory.
- Afterwards the repo was renamed from aiida_fleur_plugin to aiida-fleur

### Installation (new aiida plugin system):
- everything is now pip installable (pip install -e .) (not yet on pypi)
Therefore the files do not have to be copied anymore into the aiida_core source folder
(make sure to add the aiida-fleur folder to your PYTHONPATH variable)
- all modules are now importet from the aiida_fleur folder
 (example 'from aiida.tools.codespecific.fleur.convergence import fleur_convergence' -> 'from aiida_fleur.workflows.scf import fleur_scf_wc)

### Renaming
- In the process (and due to the entry points some things have to be renamed)
  The plugin in aiida (fleur_inp.fleur -> fleur.fleur; fleur_inp.fleurinp -> fleur.fleurinp; fleur_inp.fleurinputgen -> fleur.inpgen)

### Workflows
- some fine tuning of workflows. Naming scheme was introduced.
- Some first error catching and controlled shutdown (because of new AiiDA features).
- added consistent through all workflows the 'serial' key in wf_parameter nodes, which will turn of mpi.
- scf now uses minDistance and passes the walltime to fleur by default.

### Dokumentation
- Due to the new plugin system of AiiDA the Dokumentation is now online on read-the-docs.
(so far incomplete because of old AiiDA version on pypi) We still recommend to take a look at the docs in the repo itself (ggf build it)

### Utils
- read fleur cif folder does not break the proverance any more


### Further stuff
- 0.28 Fleur schema added to aiida-fleur



## v0.2.0 tutorial version

Version for used at the MAX AiiDA-fleur tutorial in May 2017

### Dokumentation
- added some basic explainations pages beyond the pure in code docs


### Tests
- added basic tests of Fleur itself and tests for submission

### Ploting
- There is a plot_methods repo on bitbucket which has methods to visualize common workflow output nodes.

### Workflows
- first basic working workflows available
- some common workflow stuff is now in common_fleur_wf.py

### Fleurmodifier
- Introduction of the Fleurinpmodifier class, to change fleurinp data

### Fleurinp data
- restructureing of fleurinp data and Fleurinpmodifier, moved most xml methods into xml_util
- plus added further xml routines and rough tests.


## v0.1 Base commit

### Moved everything von bitbucket to github

### Dokumentation
-Basic docs available locally

### Installation
- provided copy_files script to copy the plugin files into AiiDA folder

### Workflows
- Some basic sketches of basic workflows available (working AiiDa workflow system just released)i
