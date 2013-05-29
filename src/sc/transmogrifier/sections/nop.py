# -*- coding: utf-8 -*-
# Author: João S. O. Bueno

import base64

from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import ThouShallNotPass, NothingToDoHere


@blueprint("sc.transmogrifier.nop")
class DonothingBlueprint(BluePrintBoiler):
    """NOP:
     does nothing
     use ina  base pipeline configuratin file to create blueprint slots of
     transforms neede in derivd files.
     Or - to disable base defined bluepritns in derived files
    """
