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

