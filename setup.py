# -*- coding:utf-8 -*-
from setuptools import setup, find_packages

import os

version = '0.3'

long_description = (open("README.rst").read() + "\n" +
                    open(os.path.join("docs", "CONTRIBUTORS.txt")).read() + "\n" +
                    open(os.path.join("docs", "CHANGES.txt")).read())

setup(name='sc.transmogrifier',
      version=version,
      description="""A blueprint for collective.transmogrifier for adding
                     redirections""",
      long_description=long_description,
      classifiers=[
          "Environment :: Web Environment",
          "Framework :: Plone",
          "Framework :: Plone :: 4.2",
          "Framework :: Plone :: 4.3",
          "Framework :: Zope3",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Operating System :: OS Independent",
          "Programming Language :: Python"
      ],
      keywords='transmogrifier blueprint plone simplesconsultoria',
      author='Leonardo Rochael Almeida, Joao S. O. Bueno',
      author_email='LeoRochael@gmail.com',
      url='http://github.com/simplesconsultoria/sc.transmogrifier',
      license='gpl',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['sc'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'collective.transmogrifier',
          'five.grok',
          # Blueprint specific:
          'plone.app.redirector',
          'five.intid',
          'plone.app.referenceablebehavior'
      ],
      extras_require={
          'develop': [
              'Sphinx',
              'manuel',
              'pep8',
              'setuptools-flakes',
          ],
          'test': [
              'interlude',
              'plone.app.testing'
          ],
      },
      entry_points="""
        [z3c.autoinclude.plugin]
        target = plone
        """,
      )
