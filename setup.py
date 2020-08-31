#!/usr/bin/python3

from setuptools import setup
from io import open

setup(
		name = 'synergy_file_reader',
		description = 'A Python parser of files generated by Synergy plate readers',
		long_description = open('README.md', encoding='utf8').read(),
		python_requires = ">=3.8",
		packages = ['synergy_file_reader'],
		install_requires = ['numpy'],
		setup_requires = ['setuptools_scm','pytest-runner'],
		tests_require = ['pytest'],
		use_scm_version = {'write_to': 'synergy_file_reader/version.py'},
		classifiers = [
				'License :: OSI Approved :: BSD License',
				'Operating System :: POSIX',
				'Operating System :: MacOS :: MacOS X',
				'Operating System :: Microsoft :: Windows',
				'Programming Language :: Python',
				'Topic :: Scientific/Engineering',
			],
	)

