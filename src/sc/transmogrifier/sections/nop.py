# -*- coding: utf-8 -*-
# Author: João S. O. Bueno

from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import blueprint

@blueprint("sc.transmogrifier.nop")
class DonothingBlueprint(BluePrintBoiler):
    """NOP

     does nothing
     use in a  base pipeline configuratin file to create blueprint slots of
     transforms needed in derived files.
     Or - to disable base defined blueprints in derived files

    """
