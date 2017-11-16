import pytest

#class test_extract_corelevels():

# TODO: test in general more results outcome.
def test_extract_corelevels_outfile_allfiles():
    """
    Extracts corelevels and atomtype imformation from example out.xml file
    """
    from aiida_fleur.tools.extract_corelevels import extract_corelevels

    outxmlfiles = get_example_outxml_files()
    
    for outfile in outxmlfiles:
        corelevel, atomtypes = extract_corelevels(outfile)
        assert bool(corelevel)
        assert bool(atomtypes)

def test_extract_corelevels_outfile_interface():
    """
    Extracts corelevels and atomtype imformation from one example out.xml file
    and check the format and values of the results.
    """
    from aiida_fleur.tools.extract_corelevels import extract_corelevels

    pass
    #outfile = 
    #corelevel, atomtypes = extract_corelevels(outfile)
    #    assert bool(corelevel)
    #    assert bool(atomtypes)

'''
# this is used in extrac_corelevels, but might make sense to test extra
def test_parse_state_card_interface():
    """
    Parses a state card as written in given example out.xml files.
    The test should fail if the format of the state card in the out.xml file changes
    and/or if the interface of the method changes
    """
    from aiida_fleur.tools.extract_corelevels import parse_state_card
'''

def test_clsshifts_to_be_interface():
    """
    Tests the interface of the clsshifts_to_be method.
    Corelevel shifts with no reference given, or an empty reference given should be ignored.
    or a warning issued.
    """
    from aiida_fleur.tools.extract_corelevels import clshifts_to_be

    reference = {'W' : {'4f7/2' : [124],'4f5/2' : [], '3p3/2' : [], '3p5/2' : [10] }, 'Be' : {'1s': [117]}}
    corelevels = {'W' : {'4f7/2' : [-0.4, 0.3],'4f5/2' : [0, 0.1]},
                 'Be' : {'1s': [0,  0.3]}, 'C' : [0.0]}
    
    res = clshifts_to_be(corelevels, reference)

    expected_results = {'Be': {'1s': [117, 117.3]}, 'W': {'4f7/2': [123.6, 124.3]}}
    assert res == expected_results
    
    # expect warning clsshifts_to_be(corelevels, reference, warn=True)
    #Warning: Reference for element: 'C' not given. I ignore these.
    #Warning: Reference corelevel '4f5/2' for element: 'W' not given. I ignore these.


def get_example_outxml_files():
    """
    helper. returns all the realativ paths to the example out.xml files.
    """
    from os import listdir
    from os.path import join   
    # from top test folder
    folder_path = './files/outxml/'
    return [join(folder_path, outfile) for outfile in listdir(folder_path) if outfile.endswith(".xml")]
    

