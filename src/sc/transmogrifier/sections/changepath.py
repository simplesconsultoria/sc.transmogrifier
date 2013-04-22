# coding: utf-8
# Author: Joao S. O. Bueno

import re

from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import NothingToDoHere

@blueprint("sc.transmogrifier.utils.changepath")
class ChangePath(BluePrintBoiler):
    """
    Aplies a regular expression substituion on the item path
    """
    def set_options(self):
        # not decoding from utf-8 - paths
        # can't contain any non-ascii characters.
        #
        self.from_regexp = self.options.get("from-regexp", "").strip()
        self.to = self.options.get("to", "").strip()

    def transmogrify(self, item):
        pathkey = self.pathkey(*item.keys())[0]
        if not self.from_regexp or not pathkey:
            raise NothingToDoHere
        new_path = re.sub(self.from_regexp, self.to, item[pathkey], count=1)
        if new_path == item[pathkey]:
            raise NothingToDoHere
        if not "_orig_path" in item:
            item["_orig_path"] = item[pathkey]
        logger.info("Item %s path changed to %s" %
                    (item[pathkey], new_path))
        item[pathkey] = new_path
        return item
