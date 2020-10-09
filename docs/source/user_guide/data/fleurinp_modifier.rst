.. _fleurinp_mod:

FleurinpModifier
================

Description
-----------
The :py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` class has
to be used if you want to change anything in a stored
:py:class:`~aiida_fleur.data.fleurinp.FleurinpData`.
It will store and validate all the changes you wish to do and produce a new
:py:class:`~aiida_fleur.data.fleurinp.FleurinpData` node
after you are done making changes and apply them.

:py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` provides a
user with methods to change the Fleur input.
In principle a user can do everything, since he could prepare a FLEUR input himself and create a
:py:class:`~aiida_fleur.data.fleurinp.FleurinpData` object from that input.

.. note::
    In the open provenance model nodes stored in the database
    cannot be changed (except extras and comments). Therefore, to modify something in a stored
    `inp.xml` file one has to create a new :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`
    which is not stored, modify it and store it
    again. However, this node would pop into existence unlinked in the database and this would mean
    we loose the origin from what data it comes from and what was done to it. This is the task of
    :py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier`.

Usage
------
To modify an existing :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, a
:py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` instance
has to be initialised staring from the
:py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.
After that, a user should register
certain modifications which will be cached and can be previewed. They will be applied on
a new :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`
object when the freeze method is executed. A code example:

.. code-block:: python

  from aiida_fleur.data.fleurinpmodifier import  FleurinpModifier

  F = FleurinpData(files=['inp.xml'])
  fm = FleurinpModifier(F)                                # Initialise FleurinpModifier class
  fm.set_inpchanges({'dos' : True, 'Kmax': 3.9 })         # Add changes
  fm.show()                                               # Preview
  new_fleurinpdata = fm.freeze()                          # Apply

The figure below illustrates the work of the
:py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` class.

.. image:: images/fleurinpmodifier.png
    :width: 100%
    :align: center

User Methods
------------

General methods
_______________

    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.validate()`: Tests if
      the changes in the given list are validated.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.freeze()`: Applies all the
      changes in the list, calls
      :py:func:`~aiida_fleur.data.fleurinpmodifier.modify_fleurinpdata()` and
      returns a new :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` object.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.changes()`: Displays the
      current list of changes.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.show()`:  Applies
      the modifications and displays/prints the resulting ``inp.xml`` file. Does not generate a new
      :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` object.

.. _modify_methods:

Modification registration methods
_________________________________
The registration methods can be separated into two groups. First of all,
there are XML methods that require deeper knowledge about the structure of an ``inp.xml`` file.
All of them require an xpath input:

    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.xml_set_attribv_occ()`: Set an
      attribute of a specific occurrence of xml elements
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.xml_set_first_attribv()`: Set
      an attribute of first occurrence of xml element
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.xml_set_all_attribv()`: Set
      attributes of all occurrences of the xml element
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.xml_set_text()`: Set the text
      of first occurrence of xml element
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.xml_set_text_occ()`: Set
      an attribute of a specific occurrence of xml elements
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.xml_set_all_text()`: Set
      the text of all occurrences of the xml element
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.create_tag()`: Insert
      an xml element in the xml tree.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.delete_att()`: Delete
      an attribute for xml elements from the xpath evaluation.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.delete_tag()`: Delete
      an xml element.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.replace_tag()`: Replace
      an xml element.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.add_num_to_att()`: Adds
      a value or multiplies on it given attribute.

On the other hand, there are shortcut methods that already know some paths:

    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_species()`: Specific
      user-friendly method to change species parameters.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_atomgr_att()`:  Specific
      method to change atom group parameters.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_species_label()`: Specific
      user-friendly method to change a specie of an atom with a certain label.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_atomgr_att_label()`:  Specific
      method to change atom group parameters of an atom with a certain label.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_inpchanges()`: Specific
      user-friendly method for easy changes of attribute key value type.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.shift_value()`: Specific
      user-friendly method to shift value of an attribute.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.shift_value_species_label()`: Specific
      user-friendly method to shift value of an attribute of an atom with a certain label.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_nkpts()`: Specific
      method to set the number of kpoints.
    * :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_nmmpmat()`: Specific 
      method for initializing or modifying the density matrix file for a LDA+U calculation (details see below)

The figure below shows a comparison between the use of XML and shortcut methods.

.. image:: images/registration_methods.png
    :width: 100%
    :align: center

Modifying the density matrix for LDA+U calculations
---------------------------------------------------

The above mentioned :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_nmmpmat()` takes a special
role in the modification registration methods, as the modifications are not done on the ``inp.xml`` file but the
density matrix file ``n_mmp_mat`` used by Fleur for LDA+U calculations. The resulting density matrix file is stored
next to the ``inp.xml`` in the new :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance produced by calling
the :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.freeze()` method and will be used as the initial
density matrix if a calculation is started from this :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.

The code example below shows how to use this method to add a LDA+U procedure to a atom species and provide
an initial guess for the density matrix.

.. code-block:: python

  from aiida_fleur.data.fleurinpmodifier import  FleurinpModifier

  F = FleurinpData(files=['inp.xml'])
  fm = FleurinpModifier(F)                                                             # Initialise FleurinpModifier class
  fm.set_species('Nd-1',{'ldaU': {'l': 3, 'U': 6.76, 'J': 0.76, 'l_amf': 'F'}})        # Add LDA+U procedure
  fm.set_nmmpmat('Nd-1',orbital=3,spin=1,occStates=[1,1,1,1,0,0,0])                    # Initialize n_mmp_mat file with the states
                                                                                       # m = -3 to m = 0 occupied for spin up
                                                                                       # spin down is initialized with zeros by default
  new_fleurinpdata = fm.freeze()                                                       # Apply

.. note::
    The ``n_mmp_mat`` file is a simple text file with no knowledge of which density matrix block corresponds to which
    LDA+U procedure. They are read in the same order as they appear in the ``inp.xml``. For this reason the ``n_mmp_mat``
    file can become invalid if one adds/removes a LDA+U procedure to the ``inp.xml`` after the ``n_mmp_mat`` file was 
    initialized. To circumvent these problems always remove any existing ``n_mmp_mat`` file from the 
    :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` instance, before adding/removing or modifying the LDA+U configuration.
    Furthermore the :py:func:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier.set_nmmpmat()` should always be called 
    after any modifications to the LDA+U configuration.
    

.. Node graphs
.. -----------

.. 1. After any modification was applied to fleurinpData the following nodes will be found in the
      database to keep the Provenance

.. 2. extract kpoints
.. 3. extract structuredata
.. 4. extract parameterdata
