# -*- coding: utf-8 -*-
"""
setup: usage: pip install -e .[graphs]
"""

from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='aiida-fleur',
        version='0.1b',
        description='AiiDA Plugin for running the FLEUR-code and its input generator. Plus some utility',
        url='https://github.com/broeder-j/aiida_fleur_plugin',
        author='Jens Broeder',
        author_email='haeuselm@epfl.ch',
        license='MIT License, see LICENSE.txt file.',
        classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Plugins',
            'Framework :: AiiDA',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2.7',
            'Topic :: Scientific/Engineering :: Physics'
        ],
        keywords='fleur aiida inpgen workflows',
        packages=find_packages(exclude=['aiida']),
        include_package_data=True,
        setup_requires=[
            'reentry'
        ],
        reentry_register=True,
        install_requires=[
            'aiida-core',
            'ase',
            'lxml >= 3.6.4'
        ],
        extras_require={
            'graphs': ['matplotlib'],
        },
        entry_points={
            'aiida.calculations': [
                'fleur.fleur = aiida_fleur.calculation.fleur:FleurCalculation',
                'fleur.inpgen = aiida_fleur.calculation.fleurinputgen:FleurinputgenCalculation',
            ],
            'aiida.data': [
                'fleur.fleurinp = aiida_fleur.data.fleurinp:FleurinpData',
                'fleur.fleurinpmodifier = aiida_fleur.data.fleurinpmodifier:FleurinpModifier',
            ],
            'aiida.parsers': [
                'fleur.fleurparser = aiida_fleur.parsers.fleur:FleurParser',
                'fleur.fleurinpgenparser = fleur.inpgenparser = aiida_fleur.parsers.fleur_inpgen:FleurinputgenParser'
            ]

        },
    )
