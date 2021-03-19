from . import sql_db
from . import models
from . import fields
from . import errors
from . import apps

import sys
import os

_ROOT_DIR = ''
if getattr(sys, 'frozen', False):
    _ROOT_DIR = os.path.dirname(sys.executable)
elif __file__:
    _ROOT_DIR = os.path.dirname(os.path.dirname(__file__))