# -*- coding: utf-8 -*-
"""
setup: usage: pip install -e .[graphs]
"""

from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='aiida-fleur-advanced-wcs',
        version='0.1b',
        description='AiiDA Workchains turnkey solutions using the FLEUR-code and its input generator. Plus some utility',
        url='https://bitbucket.org/broeder-j/aiida_fleur_corelevel_wf',
        author='Jens Broeder',
        author_email='j.broeder@fz-juelich.de',
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
        keywords='fleur aiida inpgen workflows flapw juelich dft all-electron',
        packages=find_packages(exclude=['aiida']),
        include_package_data=True,
        setup_requires=[
            'reentry'
        ],
        reentry_register=True,
        install_requires=[
            'aiida-core',
            'aiida-fleur',
            'ase',
            'lxml >= 3.6.4'
        ],
        extras_require={
            'graphs': ['matplotlib'],
        },
        entry_points={
            'aiida.workflows': [
                'fleur.init_cls = aiida_fleur.workflows.initial_cls:fleur_inital_cls_wc',
                'fleur.corehole = aiida_fleur.workflows.corehole:fleur_corehole_wc',
                'fleur.corelevel = aiida_fleur.workflows.corelevel:fleur_corelevel_wc',
                #'fleur.xps = aiida_fleur.workflows.xps:fleur_xps_wc'
           ]
        },
    )
