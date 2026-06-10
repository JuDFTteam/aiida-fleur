###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
"""
Tests for the Jij workflow helpers.
"""
import io

import pandas as pd
import pytest

from aiida import orm


@pytest.mark.usefixtures('aiida_profile', 'clear_database')
def test_extract_jij_tensor_data(monkeypatch):
    """
    Test the postprocessing calcfunction for the Jij tensor.
    """
    from aiida_fleur.workflows import jij as jij_module

    def fake_calculate_heisenberg_tensor(_handle, reference_atom, onsite_delta, max_shells=None):
        assert reference_atom == 1
        assert onsite_delta.tolist() == [[0.0, 1.5, 2.5]]
        assert max_shells == 2
        return pd.DataFrame({
            'R': [1.0],
            'R_ij_x': [0.0],
            'R_ij_y': [0.0],
            'R_ij_z': [1.0],
            'Atom i': ['Fe(Fe)'],
            'Atom j': ['Fe(Fe)'],
            'J_xx': [1.0],
            'J_xy': [2.0],
            'J_xz': [3.0],
            'J_yx': [4.0],
            'J_yy': [5.0],
            'J_yz': [6.0],
            'J_zx': [7.0],
            'J_zy': [8.0],
            'J_zz': [9.0],
        })

    def fake_decompose_jij_tensor(dataframe, moment_direction):
        dataframe = dataframe.copy()
        dataframe['moment_direction'] = moment_direction
        dataframe['J_ij'] = [3.0]
        dataframe['A_ij'] = [-2.0]
        dataframe['S_ij'] = [3.0]
        dataframe['D_ij'] = [-1.0]
        return dataframe

    monkeypatch.setattr(jij_module, 'calculate_heisenberg_tensor', fake_calculate_heisenberg_tensor)
    monkeypatch.setattr(jij_module, 'decompose_jij_tensor', fake_decompose_jij_tensor)

    folder = orm.FolderData()
    folder.put_object_from_filelike(io.BytesIO(b'greensf'), 'greensf.hdf')
    folder.store()

    parameters = orm.Dict(
        dict={
            'reference_atom': 1,
            'onsite_delta': [[0.0, 1.5, 2.5]],
            'moment_direction': 'z',
            'max_shells': 2,
        })

    result = jij_module.extract_jij_tensor_data(folder, parameters)

    tensor_data = result['jij_tensor_data']
    assert tensor_data.get_dict()['moment_direction'] == 'z'
    assert tensor_data.get_dict()['data'][0]['J_ij'] == 3.0

    tensor_file = result['jij_tensor_file']
    with tensor_file.open('r') as handle:
        csv_content = handle.read()
    assert 'J_xx' in csv_content
    assert 'J_ij' in csv_content
