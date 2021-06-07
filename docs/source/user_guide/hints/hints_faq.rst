Hints/FAQ
=========


For Users
+++++++++

.. topic:: Common Errors, Traps:

    1. Wrong AiiDA datatype/Data does not have function X. Sometimes if the daemon is restarted (and something in the plugin files might have changed) AiiDA will return node of the superclasses, and not the plugin classes, which will be caught by
       some assert, or some methods will be called that are not implemented in the baseclasses. If you are a user, goto the plugin folder and delete all '.pyc' files. And restart the daemon. Restarting jupyter-notebook, might also help.
       You have to clear the old plugin classes from the cache.
       If you are a developer, this might also be because there is still some bug in the used class, and the plugin system of AiiDA cannot load it. Therefore check you development environment for simple syntax errors and others. 
       Also checking if the python interpreter runs through on the file, or checking with pylint might help. 
       ``$reentry scan aiida`` might also help, if plugin code was changed.
    
    2. TypeError: super(type, obj): obj must be an instance or subtype of type. This has a similar reason as 1. The class was changed and was not yet initialize by AiiDA. restart the daemon and clear .pyc files. If this happens for a subworkflow class
       it might also help to also import the subworkflow in your nodebook/pythonscript.
    
    3. Submission fails.
       If it is a first calculation to a computer check if the resource is available. Check the log of the calculation. Run verdi computer test. This might also be due to reason 1. if it is a followup simulations that does 
       something with data produced by an other calculation before, but the output had the wrong type.


FAQ
+++

to come
