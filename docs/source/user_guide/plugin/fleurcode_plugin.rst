.. _fleurcode_plugin:

FLEUR code plugin
=================


Description
'''''''''''
Use the plugin to support inputs of the Fleur code i.e. the ``fleur`` and ``fleur_MPI`` executables.

Supported codes
'''''''''''''''
* Tested for Fleur v0.27 (MAX release 2.0). It is NOT back compatible to
  version v0.26 and earlier, because the I/O has changed completely and the plugin
  relies on the xml I/O.

Not supported code features
'''''''''''''''''''''''''''''''''

* sparring multiple fleur calculation with on execution of fleur in a certain subdir structure
  (on can parse the commandline switches, but it will fail, because the subdirs have to be prepared
  on the machine.)
* 1D, not supported by the plugin, but currently also not tested in Fleur 0.27
  (in principal possible, some plugin functionalities have to be updated.)


Partially supported
.......................

* J_ij and D_ij calculations will be available soon.
* LDA+U, hybrid functionals and Wannier 90 not tested, in principal possible, but user ha
  to take care of copying the extra files, not all information is parsed.

Sketch of nodes
'''''''''''''''
.. image:: images/fleur_calc.png
    :width: 100%
    :align: center

Inputs
''''''
* **fleurinp**: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, optional -
  Data structure which represents the inp.xml file and everything a Fleur calculation needs.
  For more information see :ref:`FleurinpData <fleurinp_data>`.
* **parent_folder**: :py:class:`~aiida.orm.RemoteData`, optional -
  If specified, certain files in the previous Fleur calculation folder are
  copied in the new calculation folder.

.. note::
        **fleurinp** and **parent_folder** are both optional. Depending
        on the setup of the inputs, one of five scenarios will happen:

          1. **fleurinp**: files belonging to **fleurinp** will be used as input for
             FLEUR calculation.
          2. **fleurinp** + **parent_folder** (FLEUR): files, given in **fleurinp**
             will be used as input for FLEUR calculation. Moreover, initial charge density will be
             copied from the folder of the parent calculation.
          3. **parent_folder** (FLEUR): Copies inp.xml file and initial
             charge density from the folder of the parent FLEUR calculation.
          4. **parent_folder** (input generator): Copies inp.xml file
             from the folder of the parent inpgen calculation.
          5. **parent_folder** (input generator) + **fleurinp**: files belonging to
             **fleurinp** will be used as input for FLEUR calculation. Remote folder is ignored.

Outputs
'''''''
All the outputs can be found in ``calculation.outputs``.

* **fleurinp**: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` -
  See :ref:`FleurinpData <fleurinp_data>`. This output contains inp.xml that was actually
  used in the calculation. It is not always the same as an input
  :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`.
* **output_parameters**: :py:class:`~aiida.orm.Dict` -
  Contains all kinds of information of the calculation
  and some physical quantities of the last iteration.

An example output node:

  .. literalinclude:: output_node_example.py

.. note::
          The 'simple' output node will evolve. A draft of a second complex output node which
          contains informations of all iterations and atomtypes exists, but a dictionary is not
          the optimal structure for this. For now this is postponed. In any case if you want to
          parse something from the out.xml checkout the methods in xml_util.

Errors
''''''

Errors of the parsing are reported in the log of the calculation (accessible
with the ``verdi process report`` command).
Everything that Fleur writes into stderr is also shown here, i.e all JuDFT error messages.
Example:

.. code-block:: bash

      (aiidapy)% verdi process report 513
      *** 513 [scf: fleur run 1]: None
      *** (empty scheduler output file)
      *** (empty scheduler errors file)
      *** 3 LOG MESSAGES:
      +-> ERROR at 2019-07-17 14:57:01.108964+00:00
      | parser returned exit code<107>: FLEUR calculation failed.
      +-> ERROR at 2019-07-17 14:57:01.097337+00:00
      | FLEUR calculation did not finishsuccessfully.
      +-> WARNING at 2019-07-17 14:57:01.056220+00:00
      | The following was written into std error and piped to out.error : 
      |  I/O warning : failed to load external entity "relax.xml"
      | rm: cannot remove ‘cdn_last.hdf’: No such file or directory
      | **************juDFT-Error*****************
      | Error message:e>vz0
      | Error occurred in subroutine:vacuz
      | Hint:Vacuum energy parameter too high
      | Error from PE:0/24


Moreover, all warnings and errors written by Fleur in the out.xml file are stored in the
ParameterData under the key ``warnings``, and are accessible with ``Calculation.res.warnings``.

More serious FLEUR calculation failures generate a non-zero exit code. If the exit code is zero,
that means FLEUR calculation finished successfully:

.. code-block:: bash

    (aiidapy)$ verdi process list -a -p 1
       PK  Created    State             Process label             Process status
     ----  ---------  ----------------  ------------------------  ----------------------------------
       60  3m ago     ⏹ Finished [0]    FleurCalculation
       68  3m ago     ⏹ Finished [105]  FleurCalculation

means that the first calculation was successful and the second one failed because it could not open
one of the output files for some reason. Each exit code has it's own reason:

+-----------+-----------------------------------------+
| Exit code | Reason                                  |
+-----------+-----------------------------------------+
| 105       | One of output files can not be opened   |
+-----------+-----------------------------------------+
| 106       | No retrieved folder found               |
+-----------+-----------------------------------------+
| 107       | FLEUR calculation failed                |
+-----------+-----------------------------------------+
| 108       | XML output file was not found           |
+-----------+-----------------------------------------+
| 109       | Some required files were not retrieved  |
+-----------+-----------------------------------------+
| 110       | Parsing of XML output file failed       |
+-----------+-----------------------------------------+
| 111       | Parsing of relax XML output file failed |
+-----------+-----------------------------------------+

Additional advanced features
''''''''''''''''''''''''''''

.. _documentation: www.flapw.de

In general see the FLEUR `documentation`_.

While the input link with name **fleurinpdata** is used for the content of the
inp.xml, additional parameters for changing the plugin behavior, can be specified in the
**settings** input, also of type :py:class:`~aiida.orm.Dict`.

Below we summarise some of the options that you can specify, and their effect.
In each case, after having defined the content of ``settings_dict``, you can use
it as input of a calculation ``calc`` by doing::

  calc.use_settings(Dict(dict=settings_dict))


Adding command-line options
...........................

If you want to add command-line options to the executable (particularly
relevant e.g. '-hdf' use hdf, or '-magma' use different libraries, magma in this case),
you can pass each option
as a string in a list, as follows::

  settings_dict = {
      'cmdline': ['-hdf', '-magma'],
  }

The default command-line of a fleur execution of the plugin looks like this for the torque
scheduler::

'mpirun' '-np' 'XX' 'path_to_fleur_executable' '-wtime' 'XXX' < 'inp.xml' > 'shell.out' 2> 'out.error'

If the code node description contains 'hdf5' in some form, the plugin will use per default hdf5,
it will only copy the last hdf5 density back, not the full cdn.hdf file.
The Fleur execution line becomes in this case::

'mpirun' '-np' 'XX' 'path_to_fleur_executable' '-last_extra' '-wtime' 'XXX' < 'inp.xml' > 'shell.out' 2> 'out.error'


Retrieving more files
.....................

AiiDA-FLEUR does not copy all output files generated by a FLEUR calculation. By default, the plugin
copies only ``out.xml``, ``out``, ``cdn1`` and ``inp.xml``.
Depending on certain switches in used inp.xml, a plugin
is capable of automatically adding additional files to the copy list:

  * if ``band=T`` : ``bands.1``, ``bands.2``
  * if ``dos=T`` : ``DOS.1``, ``DOS.2``
  * if ``pot8=T`` : ``pot*``
  * if ``l_f=T`` : ``relax.xml``

If you know that your calculation is producing additional files that you want to
retrieve (and preserve in the AiiDA repository in the long term), you can add
those files as a list as follows (here in the case of a file named
``testfile.txt``)::

  settings_dict = {
    'additional_retrieve_list': ['testfile.txt'],
  }

Retrieving less files
.....................

If you know that you do not want to retrieve certain files(and preserve in the AiiDA repository
in the long term). i.e. the ``cdn1`` file is to large and it is stored somewhere else anyway,
you can add those files as a list as follows (here in the case of a file named
``testfile.txt``)::

  settings_dict = {
    'remove_from_retrieve_list': ['testfile.txt'],
  }

Copy more files remotely
........................

The plugin copies by default the ``broyd*`` files if a parent_folder is given
in the input.

If you know that for your calculation you need some other files on the remote machine, you can add
those files as a list as follows (here in the case of a file named
``testfile.txt``)::

  settings_dict = {
    'additional_remotecopy_list': ['testfile.txt'],
  }

Copy less files remotely
........................

If you know that for your calculation do not need some files which are copied per default by
the plugin you can add those files as a list as follows (here in the case of a file named
``testfile.txt``)::

  settings_dict = {
    'remove_from_remotecopy_list': ['testfile.txt'],
  }
