#!/usr/bin/env python
"""
setup: usage: pip install -e .[graphs]
"""
from setuptools import setup, find_packages
import json

if __name__ == '__main__':
    # Provide static information in setup.json
    # such that it can be discovered automatically
    with open('setup.json', encoding='utf-8') as info:
        kwargs = json.load(info)
    with open('README.md', encoding='utf-8') as file:
        readme_content = file.read()
    setup(
        packages=find_packages(exclude=['tests*']),
        # this doesn't work when placed in setup.json (something to do with str type)
        package_data={
            '': ['*'],
        },
        long_description=readme_content,
        long_description_content_type='text/markdown',
        **kwargs)
