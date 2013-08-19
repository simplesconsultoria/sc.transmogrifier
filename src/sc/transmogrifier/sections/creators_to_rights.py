# coding: utf-8
# Author: Joao S. O. Bueno

import ast
import re

from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import NothingToDoHere

@blueprint("sc.transmogrifier.utils.creators_to_rights")
class ChangePath(BluePrintBoiler):
    """Copies the "Creator" fields to "Rights" - used in some content types


    """

    #TODO: Use the new stule for setting options

    def set_options(self):
        self.from_ = self.options.get("from", "creators")
        self.to = self.options.get("to", "rights")
        self.flatten = ast.literal_eval(self.options.get("flatten", "True"))
        self.overwrite = ast.literal_eval(self.options.get(
                         "overwrite", "False"))
        self.types = [x.strip()
             for x in self.options.get("types", "Image").split(",")
             if x]

    def transmogrify(self, item):
        if self.get_type(item) not in self.types or self.from_ not in item:
            raise NothingToDoHere
        if not self.overwrite and item.get(self.to, None):
            raise NothingToDoHere
        value = item[self.from_]
        if isinstance(value, (tuple, list)) and self.flatten:
            value = u" ".join(value)
        item[self.to] = value

        logger.debug("""Copied field "creators" to "rights" at %s""" %
                 item.get(self.pathkey(*item.keys())[0], "<without path>"))
        return item