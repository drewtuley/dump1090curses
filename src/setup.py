__author__ = "andrew.tuley"
__date__ = "$28-Apr-2015 08:35:50$"

from setuptools import setup, find_packages

setup (
       name='dump1090curses',
       version='0.1',
       packages=find_packages(),

       # Declare your packages' dependencies here, for eg:
       install_requires=['foo>=3'],

       # Fill in these to make your Egg ready for upload to
       # PyPI
       author='andrew.tuley',
       author_email='',

       summary='Just another Python package for the cheese shop',
       url='',
       license='',
       long_description='Long description of the package',

       # could also include long_description, download_url, classifiers, etc.

  
       )