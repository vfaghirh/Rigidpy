# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='rigidpy',
    version='0.0.2',
    description='rigidpy package for rigidity analysis',
    long_description=readme,
    keywords='rigidity physics math python flexibility condensedmatter',
    author='Varda Faghir Hagh',
    author_email='vardahagh@uchicago.edu',
    url='https://github.com/vfaghirh/rigidpy',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
