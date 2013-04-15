# coding: utf-8
# Author: Joao S. O. Bueno


from sc.transmogrifier import logger

from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import normalize_string
from sc.transmogrifier.utils import NothingToDoHere, ThouShallNotPass




@blueprint("sc.transmogrifier.utils.asciify")
class SimplesFieldASCIIFicator(BluePrintBoiler):

    def set_options(self):
        self.types = set(x.strip()
                      for x in self.options.get("types", "").split(",")
                      if x)
        self.fields = set(x.strip()
                      for x in self.options.get("fields", "byline, creators").split(",")
                      if x)

    def transmogrify(self, item):
        if self.get_type(item) not in self.types:
            raise NothingToDoHere
        keys = self.fields.intersection(item.keys())
        for key in keys:
            original = item[key]
            if isinstance(item[key], (tuple, list)):
                single = False
                values = item[key]
            else:
                single = True
                values = (item[key],)
            new_values = []
            for value in values:
                new_values.append(normalize_string(value))
            item[key] = new_values[0] if single else new_values
            if item[key] != original:
                logger.info("Field %s of item at %s modified to 7bit as %s" %
                            (key, self.get_path(item), item[key]))
        return item



