# test all routines used by the fleur parser
# TODO: implement all


# parse_xmlout_file
def test_parse_xmlout_file():
    """
    tests if the routine that parsers the outputfile, produces the right output, no aiida datastructures,
    with the right content
    """
    from aiida_fleur.parsers.fleur import parse_xmlout_file
    pass
    



# parse_dos_file, test for different dos files with spin and without
def parse_dos_file():
    """
    test for the fleur dos file parser. test if right output, datastructures are produced without error
    """
    from aiida_fleur.parsers.fleur import parse_dos_file
    pass
    
    # test if array data is prodcued without error


# parse_bands_file
def test_parse_bands_file():
    """
    test for band file parse routine.
    """

    from aiida_fleur.parsers.fleur import parse_bands_file
    pass

    # test if a bandsdata object is produced
    



# test the full parser itself. on all kinds of different output files.

# test if the right aiida datastructures are produced for different output
# also check if errors are working...
# if an empty and broken file works, broken before and after first iteration


