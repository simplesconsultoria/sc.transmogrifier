from setuptools import setup, find_packages
import os

version = '0.1'

long_description = (
    open('README.txt').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.txt').read()
    + '\n' +
    open('CHANGES.txt').read()
    + '\n')

tests_require = [
    'plone.app.testing',
]

setup(name='transmogrify.redirector',
      version=version,
      description="A blueprint for collective.transmogrifier for adding redirections",
      long_description=long_description,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Plone :: 4.2",
        "Framework :: collective.transmogrifier :: Blueprint",
        ],
      keywords='',
      author='Leonardo Rochael Almeida',
      author_email='LeoRochael@gmail.com',
      url='http://pypi.python.org/pypi/transmogrify.redirector',
      license='GPL2',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['transmogrify'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'collective.transmogrifier',
          'plone.app.redirector',
      ],
      tests_require=tests_require,
      extras_require=dict(tests=tests_require),
      entry_points="""
        [z3c.autoinclude.plugin]
        target = plone
        """,
      )
