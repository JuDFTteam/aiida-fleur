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

### Dokumentation
- Due to the new plugin system of AiiDA the Dokumentation is now online on read-the-docs. 
(so far incomplete because of old AiiDA version on pypi) We still recommend to take a look at the docs in the repo itself (ggf build it)



## v0.2.0 tutorial version

Version for used at the MAX AiiDA-fleur tutorial in May 2017

### Dokumentation
- added some basic explainations pages beyond the pure in code docs


### Tests
- added basic tests of Fleur itself and tests for submission

### Ploting
- There is a plot_methods repo on bitbucket which has methods to visualize common workflow output nodes.




## v0.1 Base commit

### Moved everything von bitbucket to github

### Dokumentation
-Basic docs available locally

### Installation
- provided copy_files script to copy the plugin files into AiiDA folder

### Workflows
- Some basic sketches of basic workflows available (working AiiDa workflow system just released)
