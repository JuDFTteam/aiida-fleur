To build the documentation in sphinx, from this folder
run::

  make html

or run::

  sphinx-build -b html -d build/doctrees  -nW source build/html

This generates a html documentation tree under docs/build/html

You can browse to docs/build/html/index.html to see the documentation
in html format.

.. note:: However, that this requires to have AiiDA already installed
  on your computer (and sphinx installed, too). 
  All requirements should be met however by installing 'pip -e .[docs]'.

  If you received a distribution file, you should already find
  the compiled documentation in docs/build/html/index.html.

.. note:: for a nicer html format, install the Read The Docs theme,
  using::
  
    sudo pip install sphinx_rtd_theme 
