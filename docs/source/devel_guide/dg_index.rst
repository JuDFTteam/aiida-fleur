Developer's guide
=================

This is the developers guide for AiiDA-FLEUR

.. contents::

Package layout
++++++++++++++

All source code is under 'aiida_fleur/'

============  ============================================================
Folder name   Content
============  ============================================================
calculation   Calculation plugin classes. Each within his own file.
cmdline       The ``aiida-fleur`` click command line interface.
common        Shared defaults and node generators.
data          Data structure plugins, each with his own file.
parsers       Parsers of the package, each has its own source file.
tools         Everything using, common used functions and workfunctions
workflows     All workchain/workflow classes, each has its own file.
============  ============================================================

The XML schemas and the ``inp.xml``/``out.xml`` parsers are **not** in this package: they come from
the ``pyfleur`` dependency (``pyfleur.io.parsers.fleur_schema``), which replaced ``masci-tools`` in
3.0.0. Anything that does not depend on AiiDA belongs there rather than here.

The test suite lives in the repository-root ``tests/`` folder, not inside the package.
Documentation is fully contained within the docs folder. The rest of the files are needed
for python packaging or continuous integration things.

Automated tests
+++++++++++++++

Every decent software should have a set of rather fast tests which can be run after every commit.
The more complete all code features and code lines are tested the better. Read the unittest design guidelines on the web.
Through idealy there should be only one test(set) for one 'unit', to ensure that 
if something breaks, it stays local in the test result. Tests should be clearly understanble and documented.
 
You can run the continuous integration tests of aiida-fleur via
(for this make sure that postgres 'pg_ctl' command is in your path)::

  cd tests/
  ./run_all_cov.sh


the output should look something like this::

    (env_aiida)% ./run_all.sh 
    ======================================= test session starts ================================
    platform darwin -- Python 2.7.15, pytest-3.5.1, py-1.5.3, pluggy-0.6.0
    rootdir: /home/github/aiida-fleur, inifile: pytest.ini
    plugins: cov-2.5.1
    collected 166 items                                                                                                                                                                                          
    
    test_entrypoints.py ............                                                      [  7%]
    data/test_fleurinp.py ................................................................[ 63%]
    parsers/test_fleur_parser.py ........                                                 [ 68%]
    tools/test_common_aiida.py .                                                          [ 68%]
    tools/test_common_fleur_wf.py ..                                                      [ 69%]
    tools/test_common_fleur_wf_util.py ..........                                         [ 75%]
    tools/test_element_econfig_list.py .......                                            [ 80%]
    tools/test_extract_corelevels.py ...                                                  [ 81%]
    tools/test_io_routines.py ..                                                          [ 83%]
    tools/test_parameterdata_util.py ..                                                   [ 84%]
    tools/test_read_cif_folder.py .                                                       [ 84%]
    tools/test_xml_util.py ................                                               [ 94%]
    workflows/test_workflows_builder_init.py .........                                    [100%]
    
    ---------- coverage: platform darwin, python 2.7.15-final-0 ----------
    Name                                                           Stmts   Miss  Cover   Missing
    --------------------------------------------------------------------------------------------
    ./aiida_fleur/__init__.py                            2      0   100%
    ./aiida_fleur/calculation/__init__.py                1      0   100%
    ./aiida_fleur/calculation/fleur.py                 305    284     7%   43-221, xxx
    ./aiida_fleur/calculation/fleurinputgen.py         264    234    11%   40-63, xxx
    ./aiida_fleur/data/__init__.py                       1      0   100%
    ./aiida_fleur/data/fleurinp.py                     409    132    68%   85-86, xxx
    ./aiida_fleur/data/fleurinpmodifier.py             175     69    61%   72, 65, xxx
    ./aiida_fleur/fleur_schema/__init__.py               1      0   100%
    ./aiida_fleur/fleur_schema/schemafile_index.py      14      0   100%
    ./aiida_fleur/parsers/__init__.py                    4      0   100%
    ./aiida_fleur/parsers/fleur.py                     461    199    57%   50-61, 68, xxx
    ./aiida_fleur/parsers/fleur_inputgen.py             52     42    19%   46-55, 65-152
    ./aiida_fleur/tools/ParameterData_util.py           33      5    85%   48, 50, 70-73
    ./aiida_fleur/tools/StructureData_util.py          361    312    14%   39-71, 79-84, xxx
    ./aiida_fleur/tools/__init__.py                      1      0   100%
    ./aiida_fleur/tools/check_existence.py               7      7     0%   14-149
    ./aiida_fleur/tools/common_aiida.py                130     97    25%   53-73, 89-121, xxx
    ./aiida_fleur/tools/common_fleur_wf.py             260    209    20%   39, 47-51, 56-57, xxx
    ./aiida_fleur/tools/common_fleur_wf_util.py        232    108    53%   24-43, 80-102, xxx
    xxx
    --------------------------------------------------------------------------------------------
    TOTAL                                                                     7316   5332    27%
    

    
    ==================================== 166 passed in 22.53 seconds ===========================


If anything (especially a lot of tests) fails it is very likly that your
installation is messed up. Maybe some packages are missing (reinstall them by hand and report please).
Or the aiida-fleur version you have installed is not compatible with the aiida-core version you are running, 
since not all aiida-core versions are backcompatible. 
We try to not break back compability within aiida-fleur itself.
Therfore, newer versions of it should still work with older versions of the FLEUR code,
but newer FLEUR releases force you to migrate to a newer aiida-fleur version. 

The current test coverage of AiiDA-FLEUR has room to improve which is mainly due to the fact that calculations and workchains are not yet in the CI tests, because this requires more effort.
Also most functions that do not depend on AiiDA are moved out of this package.

.. topic:: Parser and fleurinp test:

    There are basic parser tests which run for every outputfile (out.xml) in folder 'tests/files/outxml/all_test/'
    If something changes in the FLEUR output or output of a certain feature or codepath, just add
    such an outputfile to this folder (try to keep the filesize small, if possible).
    
    For input file testing add input files to be tested to the 'tests/files/inpxml' folder and subfolders.
    On these files some basic fleurinpData tests are run.
    


Plugin development
++++++++++++++++++

Read the AiiDA plugin developer guide.
In general ensure the provenance and try to reduce complexity and use a minimum number of nodes.
Here some questions you should ask yourself:

.. topic:: For calculation plugins:

    * What are my input nodes, are they all needed? 
    * Is it apparent to the user how/where the input is specified?
    * What features of the code are supported/unsupported?
    * Is the plugin robust, transparent? Keep as simple/dump as possible/neccessary.
    * What are usual errors a user will do? Can they be circumvented? At least they should be caught.
    * Are AiiDA espected name convention accounted for? Otherwise it won't work.
    
.. topic:: Parsers: 

    * Is the parser robust? The parser should never fail.
    * Is the parser code modular, easy to read and understand?
    * Fully tested? Parsers are rather easy testable, do so!
    * Parsers should have a version number. Can one reparse?
    
.. topic:: For datastructure plugins:
    
    * Do you really need a new Datastructure?
    * What is stored in the Database/Attributes?
    * Do the names/keys apply with AiiDA conventions?
    * Is the ususal information the user is interested easy to query for?
    * What is stored in the Repository/Files?
    * Is the data code specific or rather general? If general it should become an extra extermal plugin.



Workflow/chain development
++++++++++++++++++++++++++

Keep in mind that a workflow is **SOFTWARE** which will be used by others and built on top of, and
**NOT** just a script. Not every task needs a workflow. Read the workchain guidelines of
AiiDA-core itself and of the aiida-quantumespresso package.

The shape every aiida-fleur workchain has -- class attributes, ``define()``, the ``wf_parameters``
merge, ``inpxml_changes``, naming, the shared exit-code allocation, which helpers to reuse and what
is machine-checked -- is documented on its own page:

.. toctree::
   :maxdepth: 2

   ./writing_workchains

The conventions it applies are listed in ``STYLE_CONVENTION.txt`` at the repository root, and the
user-facing side of the same contract is :ref:`using_workflows`.


Entrypoints
+++++++++++

In order to make AiiDA aware of any classes (plugins) like (calculations, parsers, data, workchains, workflows, commandline)
the python entrypoint system is used. Therefore, you have to register any  of the above classes as an entrypoint in the 'pyproject.toml' file.

Example, abridged from the real file::

    [project.entry-points."aiida.calculations"]
    "fleur.fleur" = "aiida_fleur.calculation.fleur:FleurCalculation"
    "fleur.inpgen" = "aiida_fleur.calculation.fleurinputgen:FleurinputgenCalculation"

    [project.entry-points."aiida.data"]
    "fleur.fleurinp" = "aiida_fleur.data.fleurinp:FleurinpData"

    [project.entry-points."aiida.parsers"]
    "fleur.fleurparser" = "aiida_fleur.parsers.fleur:FleurParser"
    "fleur.fleurinpgenparser" = "aiida_fleur.parsers.fleur_inputgen:Fleur_inputgenParser"

    [project.entry-points."aiida.workflows"]
    "fleur.scf" = "aiida_fleur.workflows.scf:FleurScfWorkChain"
    "fleur.base" = "aiida_fleur.workflows.base_fleur:FleurBaseWorkChain"
    "fleur.eos" = "aiida_fleur.workflows.eos:FleurEosWorkChain"
    "fleur.banddos" = "aiida_fleur.workflows.banddos:FleurBandDosWorkChain"
    "fleur.init_cls" = "aiida_fleur.workflows.initial_cls:FleurInitialCLSWorkChain"
    "fleur.corehole" = "aiida_fleur.workflows.corehole:FleurCoreholeWorkChain"

The left hand side is the entry point name. This name is what you pass to the Factory classes of
AiiDA (``WorkflowFactory('fleur.scf')``). The convention is that the name has two parts,
'package_name.whatevername'; the package name has to be reserved in the AiiDA registry, because
entry points must be unique. The right hand side has the form 'module_path:ClassName'.

A class is only reachable after the package is reinstalled (``pip install -e .``). See
:ref:`writing_workchains` for the workchain-specific part of this.


Documentation
+++++++++++++

Since a lot of the documentation is auto generated it is important that you give every module, class and function
proper doc strings.


For the documentation we use `sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`, which is based on restructured text, `also see <https://sublime-and-sphinx-guide.readthedocs.io/en/latest/index.html>`.
And we build and upload the documentation to `readthedocs <https://docs.readthedocs.io/en/stable/index.html>`
Also in restructured text headings are marked with some underlining, while the order is arbitrary and sphinx determines it on occurrence.
To make the whole documentation consistent it is important that you stay to the conventions of underlying.

+---------------+----------------+------------------+
| Heading level | underline with | Comment          |
+---------------+----------------+------------------+
| 0             | #              |                  |
+---------------+----------------+------------------+
| 1             | ``*``          |                  |
+---------------+----------------+------------------+
| 2             | =              | usual start here |
+---------------+----------------+------------------+
| 3             | ``+``          |                  |
+---------------+----------------+------------------+
| 4             | ``-``          |                  |
+---------------+----------------+------------------+
| 5             | ^              |                  |
+---------------+----------------+------------------+
| 6             | '              |                  |
+---------------+----------------+------------------+
| 7             | ,              |                  |
+---------------+----------------+------------------+
| 8             | .              |                  |
+---------------+----------------+------------------+

Other information
+++++++++++++++++

Google python guide, doing releases, pypi, packaging, git basics, issues, aiida logs, loglevel, ...

Useful to know
--------------

1. pip -e is your friend::

    pip install -e package_dir

Always install python packages you are working on with -e, this way the new version is used, if the files are changed, as long as the '.pyc' files are updated.

2. In jupyter/python use the magic::
   
   %load_ext autoreload
   %autoreload 2
   
This will import your classes everytime anew. Otherwise they are not reimportet if they have already importet. This is very useful for development work.
