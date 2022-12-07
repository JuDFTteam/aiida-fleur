"""
This module defines a class which supports the magnetic moment definitions
supported by the Fleur inputgenerator

Eventually this should be replaced by the a more code agnostic class
"""
from __future__ import annotations

from aiida.orm import StructureData
import sys
import numbers

from typing import Union, List, Any
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

_DEFAULT_MAGNETIC_MOMENT = None

FleurMagneticMomentDefinition: TypeAlias = List[Union[None, float, List[float], Literal['up', 'down']]]


class FleurMagneticStructureData(StructureData):
    """
    Structure Data which supports the magnetic moment definitions supported by the fleur input generator

    These are given as a list of the same length of sites and the values can be either

        1. None -> no magnetic moment definition will be set for this site
        2. a single float -> initial magnetic moment
        3. a list of three floats -> magnetic moment vector (for a non-collinear calculation)
        4. strings 'up' or 'down' -> direction of magnetic moment (collinear) with the default size
    """

    def __init__(self, magnetic_moments: FleurMagneticMomentDefinition | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        if magnetic_moments is None:
            magnetic_moments = [_DEFAULT_MAGNETIC_MOMENT] * len(self.sites)
        self.set_magnetic_moments(magnetic_moments)

    def set_magnetic_moments(self, magnetic_moments: FleurMagneticMomentDefinition) -> None:
        """
        Set the magnetic moments
        """
        from aiida.common.exceptions import ModificationNotAllowed

        if self.is_stored:
            raise ModificationNotAllowed(
                'The FleurMagneticStructureData object cannot be modified, it has already been stored')

        for mag_mom in magnetic_moments:
            if mag_mom is None:
                continue
            if isinstance(mag_mom, list):
                if len(mag_mom) != 3:
                    raise ValueError('Magnetic moment definition as a list has to have length 3')
                if not all(isinstance(m, numbers.Real) for m in mag_mom):
                    raise ValueError('Magnetic moment definition as a list has to consist of only numbers')
            elif isinstance(mag_mom, str):
                if mag_mom not in ('up', 'down'):
                    raise ValueError("Magnetic moment definition as strings only allows 'up' or 'down'")
            elif not isinstance(mag_mom, numbers.Real):
                raise ValueError('Invalid value for magnetic moment definition:'
                                 "Only None, numbers, list of three numbers or the strings 'up' or 'down' are allowed")

        self.base.attributes.set('magnetic_moments', magnetic_moments)

    @property
    def magnetic_moments(self) -> FleurMagneticMomentDefinition:
        """
        Get the magnetic moment definitions
        """
        return self.base.attributes.get('magnetic_moments')

    @magnetic_moments.setter
    def magnetic_moments(self, magnetic_moments: FleurMagneticMomentDefinition) -> None:
        """
        Set the magnetic moment definitions
        """
        self.set_magnetic_moments(magnetic_moments)

    def _validate(self):
        """
        Performs some standard validation tests.
        """
        from aiida.common.exceptions import ValidationError

        super()._validate()

        if len(self.magnetic_moments) != len(self.sites):
            raise ValidationError('Mismatch of number of magnetic moments and atom sites')
