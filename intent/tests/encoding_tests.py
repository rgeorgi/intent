import os
from unittest.case import TestCase

from intent.commands.enrich import enrich
from intent.consts import *
from intent.igt.parsing import xc_load
from intent.utils.env import xigt_testfiles
import logging
logging.basicConfig(level=logging.INFO)

