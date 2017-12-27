#!/usr/bin/env python
# -*- coding: utf-8 -*-

# test the fleur specific graph gernation routine
import pytest

# test draw_graph
@pytest.mark.usefixtures("aiida_env")
def test_draw_graph_if_produces_file():
    from aiida_fleur.tools.graph_fleur import draw_graph
    from aiida.orm import Node
    
    # TODO store a real graph and test if it is represented right...
    node = Node()
    outfile_expected = 'None.dot'
    exit_expected = 0
    exit_status, output_file_name = draw_graph(node)


    assert exit_status == exit_expected
    assert output_file_name == outfile_expected
