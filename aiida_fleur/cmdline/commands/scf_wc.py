"""
contains verdi commands for the scf workchain
in general these should become options of verdi aiida-fleur workchains 
"""

import click


@click.group()
def scf_wc():
    pass

@scf_wc.command()
def res():
    """
    Prints the result node to screen
    """
    click.echo('verdi aiida-fleur scf res')

@scf_wc.command()
def show():
    """
    plots the results of a 
    """
    click.echo('verdi aiida-fleur scf show')

@scf_wc.command()
def list():
    """
    similar to the verdi work list command, but this displays also some 
    specific information about the scfs
    """
    click.echo('verdi aiida-fleur scf list')