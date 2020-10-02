#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' Contains test the fleur specific graph gernation routine. '''
from __future__ import absolute_import
import pytest

# These tests need dot/graphviz... which is not autoinstalled in the python env... so far
# Therefore I uncomment these tests for know, because they will fail on travis.
# TODO find a way (aiidas problem) to set up a clean environment
'''
# test draw_graph
@pytest.mark.usefixtures("aiida_env")
def test_draw_graph_if_produces_file():
    """
    does the individual fleur_draw_graph routine produce a file?
    """
    import os
    from aiida_fleur.tools.graph_fleur import draw_graph
    from aiida.orm import Node

    # TODO store a real graph and test if it is represented right...
    node = Node()
    outfile_expected = 'None.dot'
    exit_expected = 0
    exit_status, output_file_name = draw_graph(node)
    os.remove(output_file_name)

    assert exit_status == exit_expected
    assert output_file_name == outfile_expected

'''
