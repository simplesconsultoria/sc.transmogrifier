# coding: utf-8

# Based on collective/transmogrifier/sections/folders.py
#
# Adaptation to time-warping on-demand folder migration
# by jsbueno@simplesconsultoria.com.br



from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
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

        items.append(item)
        return items
