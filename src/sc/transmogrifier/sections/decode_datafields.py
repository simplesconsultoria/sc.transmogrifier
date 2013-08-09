# coding: utf-8
# Author: Joao S. O. Bueno

import base64

from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import NothingToDoHere


@blueprint("sc.transmogrifier.utils.decode_datafields")
class DataFields(BluePrintBoiler):
    """ collective.jsonmigrator.datafields blueprint decodes binary
    datafields alright - but only after the objects are already
    constructed. This does the decoding on the pipeline, so that it works
    even if the object is not constructed - and so that other blueprints
    can modify the binary fields before constructing as well
    (like separating an image-field from a News Item into
    a separate image object)
    """

    OPTIONS = [("datafield_prefix", "_datafield_")]

    def transmogrify(self, item):
        for key in item.keys():
            if not key.startswith(self.datafield_prefix):
                continue

            fieldname = key[len(self.datafield_prefix):]
            field = item.pop(key)
            field["data"] = base64.b64decode(field["data"])
            item[fieldname] = field

        return item