# coding: utf-8

# Based on collective/transmogrifier/sections/folders.py
#
# Adaptation to time-warping on-demand folder migration
# by jsbueno@simplesconsultoria.com.br

import ast

from zope.interface import classProvides, implements
from collective.transmogrifier.utils import defaultMatcher

from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import normalize_url
from sc.transmogrifier.utils import NothingToDoHere, ThouShallNotPass


@blueprint("sc.transmogrifier.utils.migration_folders")
class MigrationFoldersSection(BluePrintBoiler):

    def set_options(self):
        self.newPathKey = self.options.get('new-path-key', None)
        self.newTypeKey = self.options.get('new-type-key', '_type')
        self.folderType = self.options.get('folder-type', 'Folder')
        self.cache = self.options.get('cache', 'true').lower() == 'true'

        self.use_wormhole = ast.literal_eval(
                self.options.get("use_wormhole", "False"))
        self.use_original_path = ast.literal_eval(
                self.options.get("original_path", "False"))

        # blueprint initialization
        self.seen = set()
        self.traverse = self.transmogrifier.context.unrestrictedTraverse

    def __iter__(self):
        for item in self.previous:
            try:
                items = self.transmogrify(item)
            except NothingToDoHere:
                items = [item]
            except ThouShallNotPass:
                continue
            for new_item in items:
                yield new_item

    def transmogrify(self, item):

        if "__item_encapsulated_by_sc_migration_folders" in item:
            return [item["__item_encapsulated_by_sc_migration_folders"]]

        traverse = self.traverse

        items = []
        path = self.get_path(item)

        newPathKey = self.newPathKey or self.pathkey(*item.keys())[0]
        newTypeKey = self.newTypeKey

        elems = path.strip('/').rsplit('/', 1)
        container, id = (len(elems) == 1 and ('', elems[0]) or elems)


        containerPathItems = container.split('/')

        # This may be a new container
        if container in self.seen or not containerPathItems:
            raise NothingToDoHere

        checkedElements = []

        # Check each possible parent folder
        path_exists = True
        for element in containerPathItems:
            checkedElements.append(element)
            currentPath = '/'.join(checkedElements)

            if self.cache:
                if currentPath in self.seen:
                    continue
                self.seen.add(currentPath)

            if path_exists and traverse(currentPath, None) is None:
                # Path does not exist from here on
                path_exists = False

            if not path_exists:
                # We don't have this path - yield to create a
                # skeleton folder
                new_folder = {}
                new_folder[newPathKey] = '/' + currentPath
                new_folder[newTypeKey] = self.folderType
                # Set folder to be published if item is to be as well:
                if "_transitions" in item:
                    new_folder["_transitions"] = item["_transitions"]
                logger.info("Schedulling %s folder to be created"
                            " to contain %s" % ("/" + currentPath, path))
                items.append(new_folder)

        if self.cache:
            self.seen.add("%s/%s" % (container, id,))

        if self.use_wormhole and items:
            # Send our folders back to the begining of the pipeline -
            # and put our item on a cocoon from where we will
            # free it again in the future
            # TODO: refactor the "cocoon" mechanism to
            # be more integrated in the wormhole engine

            # can't simply push our stuff to the end of the
            # wormhole - if the wormhole is not empty, it may
            # contain other items scheduled to be build after
            # the current item. And the current item needs
            # these folders to go first:
            cocoon = {"__item_encapsulated_by_sc_migration_folders": item}
            self.storage["wormhole"].appendleft(cocoon)
            for new_folder in reversed(items):
                self.storage["wormhole"].appendleft(new_folder)


            #And...hyperjump back to the beggining of the pipeline, where
            # our item will be hapily yielded by the whitehole blueprint
            raise ThouShallNotPass

        items.append(item)

        return items
