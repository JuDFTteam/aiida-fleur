Lets get started

Installation of AiiDA-FLEUR
+++++++++++++++++++++++++++


Run automated tests
-------------------

After you have installed aiida-fleur it is always a good idea to run 
the automated standard test set once to check on the installation.
(for this make sure that postgres 'pg_ctl' command is in your path)::

  cd aiida_fleur/tests/
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
    
    + coverage report
    
    ==================================== 166 passed in 22.53 seconds ===========================


If anything (especially a lot of tests) fails it is very likly that your
installation is messed up. Maybe some packages are missing (reinstall them by hand and report please).
Or the aiida-fleur version you have installed is not compatible with the aiida-core version you are running, 
since not all aiida-core versions are backcompatible. 
We try to not break back compability within aiida-fleur itself.
Therfore, newer versions of it should still work with older versions of the FLEUR code,
but newer FLEUR releases force you to migrate to a newer aiida-fleur version. 



Usage recommendations
+++++++++++++++++++++

This plugin enables you to do your DFT work with FLEUR in pure python code.
You can interact with AiiDA via python scripts, interactive shells, 
(ipython, python, verdi shell) and you can use your favorite python tools.




Tutorials
+++++++++

Basic AiiDA tutorials:
''''''''''''''''''''''
If you are not familiar with the basics of AiiDA yet, you might want to checkout
the `AiiDA youtube tutorials. <https://www.youtube.com/channel/UC-NZvRRQ5VzT2wKE5DM1N3A/playlists>`_
The jupyter notebooks from the tutorials you will find `here <https://github.com/aiidateam/aiida_demos>`_ on github,
where you can also try them out in binder.



Run inpgen calculation tutorial
'''''''''''''''''''''''''''''''
sorry, not uploaded yet

Run fleur calculation tutorial
''''''''''''''''''''''''''''''
sorry, not uploaded yet


Run fleur SCF tutorial
''''''''''''''''''''''
sorry, not uploaded yet


Run fleur eos tutorial
''''''''''''''''''''''
sorry, not uploaded yet


Run fleur bandstructure/dos tutorial
''''''''''''''''''''''''''''''''''''
sorry, not uploaded yet
