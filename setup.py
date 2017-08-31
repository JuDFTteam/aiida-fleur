# -*- coding: utf-8 -*-
"""
setup: usage: pip install -e .[graphs]
"""

from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='aiida-fleur',
        version='0.5.0',
        description='Python FLEUR simulation package containing an AiiDA Plugin for running the FLEUR-code and its input generator. Plus some workflows and utility',
        url='https://github.com/broeder-j/aiida-fleur',
        author='Jens Broeder',
        author_email='j.broeder@fz-juelich.de',
        license='MIT License, see LICENSE.txt file.',
        classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Plugins',
            #'Framework :: AiiDA',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2.7',
            'Topic :: Scientific/Engineering :: Physics',
            'Natural Language :: English'
        ],
        keywords='fleur aiida inpgen workflows flapw juelich dft all-electron',
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
                'fleur.fleurinpgenparser = aiida_fleur.parsers.fleur_inputgen:Fleur_inputgenParser'
            ],
            'aiida.workflows': [
                'fleur.scf = aiida_fleur.workflows.scf:fleur_scf_wc',
                'fleur.dos = aiida_fleur.workflows.dos:fleur_dos_wc',
                'fleur.band = aiida_fleur.workflows.band:fleur_band_wc',
                'fleur.eos = aiida_fleur.workflows.eos:fleur_eos_wc',
                'fleur.dummy = aida_fleur.workflows.dummy:dummy_wc',
                'fleur.sub_dummy = aida_fleur.workflows.dummy:sub_dummy_wc'
                'fleur.init_cls = aiida_fleur.workflows.initial_cls:fleur_inital_cls_wc',
                'fleur.corehole = aiida_fleur.workflows.corehole:fleur_corehole_wc',
                'fleur.corelevel = aiida_fleur.workflows.corelevel:fleur_corelevel_wc',
           ]
        },
    )
