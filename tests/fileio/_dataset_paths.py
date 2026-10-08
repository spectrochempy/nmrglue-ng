"""Paths shared by file-I/O tests that use the external corpus."""

import os.path

TESTS_DIR = os.path.dirname(os.path.dirname(__file__))
NMRGLUE_ROOT = os.path.dirname(TESTS_DIR)
DATA_DIR = os.path.join(NMRGLUE_ROOT, 'data')
