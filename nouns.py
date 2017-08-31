'''
Some common names for, like, common things.
'''


# 1st-party
import os


PYPI_DIRECTORY = '/var/pypi.python.org/web'
assert os.path.isdir(PYPI_DIRECTORY)

SIMPLE_DIRECTORY = os.path.join(PYPI_DIRECTORY, 'simple')
assert os.path.isdir(SIMPLE_DIRECTORY)

PACKAGES_DIRECTORY = os.path.join(PYPI_DIRECTORY, 'packages')
assert os.path.isdir(PACKAGES_DIRECTORY)


