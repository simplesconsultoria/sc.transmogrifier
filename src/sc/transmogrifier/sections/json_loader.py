# coding: utf-8
# Author: Joao S. O. Bueno


import json
import os

from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import NothingToDoHere, ThouShallNotPass


@blueprint("json.migration.source")
class Source(BluePrintBoiler):
    """
    This blueprint feeds the pipleine with records
    exported in a dirctory structure in which, each object's data
    is encoded in a json file - by default named "data.json".

    A modified version of the code in collective.jsonify can be used
    to dumo the data  from an older plone portal to disk.
    """
    OPTIONS = [
                # The folder from which the paths inside the Zope for the old portal apply
                ("base_dir", "/home/user/data/"),
                # The _path prefix for each item read:
                ("root_path", "Plone"),
                ("restrict_portal_types", None, "literal"),
                ("restrict_path", "''", "literal"),
                ("data_filename", "data.json"),
                ("offset","None", "literal"),
                ("limit","None", "literal"),
                ("debug", "True", "literal"),
                # This file should be a csv file composed of
                # the full zope path of each item, the item type and the item's UID if any.
                ("paths_file", "/home/user/object_index.csv")
    ]

    def __iter__(self):
        # Loading these parameters from the transmogrifier object
        # allow for repeated retrieval and commiting of small content blocks
        # at a time - needed when migration is in concurrence with
        # other portal modifying activity.
        # check the snippets for interactive importing at
        # the creator_mutator.py.snippets.txt file
        offset = getattr(self.transmogrifier, "brasil_source_offset",
            getattr(self, "offset", None))
        limit = getattr(self.transmogrifier, "brasil_source_limit",
            getattr(self, "limit", None))
        for item in self.previous:
            yield item
        base_path = os.path.join(self.base_dir, self.root_path)
        counter = 0

        if getattr(self.transmogrifier, "brasil_source_paths", None):
            paths = self.transmogrifier.brasil_source_paths
            print "using cached paths "
        else:
        # sshfs makes pickle from file slow
            paths = open(self.paths_file, "rb").readlines()
            self.transmogrifier.brasil_source_paths = paths

        portal_type = None
        for line in paths:
            parts = line.split(",")
            if len(parts) != 3:
                continue
            data_path, portal_type, uid = [p.strip() for p in parts]
            rel_path = data_path[len(self.base_dir) :]

            counter += 1
            if self.restrict_path not in rel_path:
                continue

            if offset and counter < offset:
                continue

            if counter % 100 == 0:
                print counter,

            if limit and counter > ((0 if offset is None else offset) + limit):
                break
            if (portal_type and self.restrict_portal_types and
                portal_type not in self.restrict_portal_types ):
                    continue
            try:
                final_path = self.base_dir + data_path.strip("/") + "/" + self.data_filename
                item = json.load(open(final_path))
            except Exception as error:
                logger.error("CRASH json reading %s: %s " % (data_path, error))
                continue


            yield item