from equipsedit import models
from equipsedit.models import Q
from equipsedit import _ROOT_DIR

import sys
import os
import inspect
# from equipsedit import apps

a = 'equipsedit.apps.users.users'

def main():
    _models = []
    model = object()
    for cls in models.Model.__subclasses__():
        c = cls()

        model = c if c._name == 'ir.model' else model
        if c._init and not c._has_created():
            c.create_table()
            _models.append(c)

    for cls in _models:
        model.create({
            'name': cls._description,
            'model': cls._name,
            'module': inspect.getmodule(cls).__file__[len(_ROOT_DIR)+1:].replace('\\', '/')
        })


if __name__ == '__main__':
    main()