"""
contains verdi commands that are useful for fleur workchains
"""


import click


@click.group()
def workchains():
    pass

@workchains.command()
def res():
    """
    Prints the result node to screen
    """
    click.echo('verdi aiida-fleur workchains res pk/uuid/list')

@workchains.command()
def show():
    """
    plots the results of a workchain
    """
    click.echo('verdi aiida-fleur workchains show pk/uuid/list')

@workchains.command()
def list():
    """
    similar to the verdi work list command, but this displays also some 
    specific information about the fleur workchains, can be filtered for 
    certain workchains...
    """
    click.echo('verdi aiida-fleur workchians list -scf -A -p')