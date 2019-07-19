.. _inpgen_plugin:

Fleur input generator plugin
============================

Description
'''''''''''
The input generator plugin is capable of running the Fleur input generator (inpgen) with all
its features, except crystal structure creation (we did not want to support that).
To submit a calculation you need to specify a :py:class:`~aiida.orm.StructureData`,
the inpgen  :py:class:`~aiida.orm.Code` and a calc_parameters: :py:class:`~aiida.orm.Dict`
containing all other parameters that inpgen accepts as an input.
As a result, an fleurinpData node
will be created which is a database representation of inp.xml and all other input files for FLEUR.

Supported code versions
''''''''''''''''''''''''
* It is tested from Fleur v0.27 (MAX release 2.0) onwards, but it should work
  for all inpgen versions.

Sketch of nodes
'''''''''''''''

.. image:: images/fleurinpgen_calc.png
    :width: 100%
    :align: center

Inputs
''''''

* **code**: :py:class:`Code <aiida.orm.Code>` - the Code node of an inpgen executable

* **structure**: :py:class:`~aiida.orm.StructureData` -
  a crystal structure

.. note::
          The plugin will run inpgen always with relative coordinates (crystal coordinates) in the
          3D case. In the 2D case in rel, rel, abs. Currently for films no crystal rotations are be
          performed, therefore the coordinates need to be given as Fleur needs them. (x, y in plane,
          z out of plane)

* **calc_parameters**: :py:class:`Dict <aiida.orm.Dict>`,
  optional -
  Input parameters of inpgen, as a nested dictionary, mapping the fortran list input of inpgen.
  Examples:

  .. literalinclude:: parameter_example.py


.. note:: 
          The ‘&atom’ namelist can occur several times in inpgen input (each key can occur only ones
          in a python dictionary). The plugin will reconize any namelist which contains the chars
          ‘atom’.

.. note:: 
          Namelists in the inpgen input without key=value (like &soc) have to be provided with the
          attributename from the inp.xml.

.. _Fleur documentation: https://www.flapw.de/site/inpgen/#basic-input

See the `Fleur documentation`_ for the full list of variables and their meaning.
Some keywords don't have to be specified and are already taken care of by AiiDA (are related with
the structure or with path to files):

defaults::

          &input film

so far not allowed/supported::

          &lattice

* **settings**: class :py:class:`Dict <aiida.orm.Dict>`, optional -
  An optional dictionary that allows the user to specify if additional files shall be received and
  other advanced non default stuff for inpgen.


Outputs
'''''''

There are several output nodes that can be created by the inpgen plugin, according to the
calculation details. All output nodes can be accessed via ``calculation.outputs``.


* **fleurinp**: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` -
  Data structure which represents the inp.xml file and provides useful methods.
  For more information see fleurinpData. (accessed by ``calculation.outputs.fleurinp``)
* **output_parameters**: :py:class:`Dict <aiida.orm.Dict>` -
  Should contain information about the inpgen run.
  Example:

  * errors  (possible error messages generated in the run)
  * warnings (possible warning messages generated in the run).
  * recommendations (other hints)
  * output information (some information parsed from the out file)

Additional advanced features
''''''''''''''''''''''''''''

While the input link with name ``calc_parameters`` is used for the content of the
namelists and parameters of the inpgen input file, additional parameters for changing the plugin
behavior can be specified in the 'settings': class :py:class:`Dict <aiida.orm.Dict>` input.

Below we summarise some of the options that you can specify and their effect.
In each case, after having defined the content of ``settings_dict``, you can use
it as input of a calculation ``calc`` by doing::

  calc.use_settings(Dict(dict=settings_dict))

Retrieving more files
.....................

The inpgen plugin retrieves per default the files : inp.xml, out, struct.xsf.

If you know that your inpgen calculation is producing additional files that you want to
retrieve (and preserve in the AiiDA repository in the long term), you can add
those files as a list as follows (here in the case of a file named
``testfile.txt``)::

  settings_dict = {
    'additional_retrieve_list': ['testfile.txt'],
  }

Retrieving less files
.....................

If you know that you do not want to retrieve certain files (and preserve in the AiiDA repository
in the long term) you can add those files as a list as follows (here in the case of a file named
``testfile.txt``)::

  settings_dict = {
    'remove_from_retrieve_list': ['testfile.txt'],
  }
