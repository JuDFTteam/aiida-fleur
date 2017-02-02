__version__ = "0.1"
__authors__ = "Jens Broeder"

from setuptools import setup, find_packages

setup(
    name='aiida-fleur',
    version='0.1',
    url='http://www.flapw.de', # on bitbucket
    license='MIT license, see LICENSE.txt',
    description='The AiiDA plugin for the all-electron DFT code FLEUR (www.flapw.de)',
    author = 'Jens Broeder',
    author_email='j.broeder@fz-juelich.de',
    #scripts=['helloworld'],


    install_requires=[
        'lxml == 3.6.4',
        'aiida>=0.7.0',
        #'fleurinpdata>='
        'ase',
        ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    packages=["aiida_fleur"],# find_packages(),
    entry_points={
            'aiida.calculations':['fleur.fleur = aiida_fleur.calculations.fleur:FleurCalculation', 'fleur.inpgen = aiida_fleur.FleurinputgenCalculation'],
            'aiida.parsers':['fleur.fleurparser = aiida_fleur.parsers.fleur:FleurParser', 'fleur.inpgenparser = aiida_fleur.parsers.fleur_inpgen:FleurinputgenParser'],
            #'aiida.data':['aiida_fleur.fleurinp = fleuplugin.data'],
            #'aiida.tools':['aiida_fleur.tools = aiida_fleur.tools'],
            }
)
