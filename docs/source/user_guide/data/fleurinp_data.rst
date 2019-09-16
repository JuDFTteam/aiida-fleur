.. _fleurinp_data:

FleurinpData
============

* **Class**: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`
* **String to pass to the** :py:func:`~aiida.plugins.DataFactory`: ``fleur.fleurinp``
* **Aim**: store input files for the FLEUR code and provide user-friendly editing.
* **What is stored in the database**: the filenames, a parsed inp.xml files as nested dictionary
* **What is stored in the file repository**: inp.xml file and other optional files.
* **Additional functionality**: Provide user-friendly methods. Connected to structure and Kpoints
  AiiDA data structures


Description/Features
--------------------

.. image:: images/fleurinpdata.png
    :width: 100%
    :align: center
..    :height: 300px


:py:class:`~aiida_fleur.data.fleurinp.FleurinpData` is an additional AiiDA data structure which
represents everything a Fleur
calculation needs, which is mainly a complete ``inp.xml`` file.

.. note::

          Currently, :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` methods support
          *ONLY* ``inp.xml`` files, which have
          everything in them (kpoints, energy parameters, ...), i.e which were created with
          the ``-explicit`` inpgen command line switch.
          In general it was designed to account for several separate files too,
          but this is no the default way Fleur should be used with AiiDA.

:py:class:`~aiida_fleur.data.fleurinp.FleurinpData` was implemented
to make the plugin more user-friendly, hide complexity and
ensure the connection to AiiDA data structures (:py:class:`~aiida.orm.StructureData`,
:py:class:`~aiida.orm.KpointsData`).
More detailed information about the methods can be found below and in the module code documentation.

.. note::

          For changing the input file use the class
          :py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` class, because a new
          :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` object has to be stored
          in the database which will be linked in the
          database over a CalcFunction to the parent :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`.
          Otherwise the provenance of from where the new :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` comes from is likely lost.

Initialization:

.. code-block:: python

  from aiida_fleur.data.fleurinp import FleurinpData
  # or FleurinpData = DataFactory('fleur.fleurinp')

  F = FleurinpData(files=['path_to_inp.xml_file', <other files>])
  #or
  F = FleurinpData(files=['inp.xml', <other files>], node=<folder_data_pk>)

If the ``node`` attribute is specified, AiiDA will try to get files from the
:py:class:`~aiida.orm.FolderData` corresponding
to the node. If not, it tries to find an ``inp.xml`` file using absolute path
``path_to_inp.xml_file``. The use of absolute paths will be deprecated in the future hence it is
recommended to always use files attached to a database node.

Be aware that the ``inp.xml`` file name has to be named 'inp.xml', i.e. no file names are
changed, the files will be given with the provided names to Fleur (so far).
Also if you add an other inp.xml file the first one will be overwritten.


Properties
----------

    * ``inp_dict``: Returns the inp_dict (the representation of the inp.xml file) as it will or is
      stored in the database.

    * ``files``: Returns a list of files, which were added to FleurinpData. Note that all of these
      files will be copied to the folder where FLEUR will be run.

    * ``_schema_file_path``: Returns the absolute path of the xml schema file used for the current
      inp.xml file.

.. note::
  ``FleurinpData`` will first look in the ``aiida_fleur/fleur_schema/input/`` for matching Fleur
  xml schema files to the ``inp.xml`` files.
  If it does not find a match there, it will recursively search in your PYTHONPATH
  and the current directory.
  If you installed the package with pip there should be no problem, as long the package versions
  is new enough for the version of the Fleur code you are deploying.

User Methods
------------

    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.del_file()` - Deletes a file from
      :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.
    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.set_file()` - Adds a file from a folder node
      to :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.
    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.set_files()` - Adds several files from a
      folder node to :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.
    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.get_fleur_modes()` - Analyse inp.xml and
      get a corresponding calculation mode.
    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.get_structuredata()` - A CalcFunction which
      returns an AiiDA :py:class:`~aiida.orm.StructureData`
      type extracted from the inp.xml file.
    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.get_kpointsdata()` - A CalcFunction which
      returns an AiiDA :py:class:`~aiida.orm.KpointsData`
      type produced from the inp.xml
      file. This only works if the kpoints are listed in the in inp.xml.
    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.get_parameterdata()` - A CalcFunction
      that extracts a :py:class:`~aiida.orm.Dict` node
      containing FLAPW parameters. This node can be used as an input for inpgen.
    * :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.set_kpointsdata()` -
      A CalcFunction that writes kpoints
      of a :py:class:`~aiida.orm.KpointsData` node in the
      inp.xml file returns a new
      :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance. It replaces old kpoints.
