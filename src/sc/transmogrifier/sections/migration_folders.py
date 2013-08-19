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


COCOON_KEY = "__item_encapsulated_by_sc_migration_folders"
@blueprint("sc.transmogrifier.utils.migration_folders")
class MigrationFoldersSection(BluePrintBoiler):
    """Retrieves and puts Container items on the pipeline

    When retrieving specific content types, often the folders
    or other contents for our conte-types are not in place yet.
    While collective.transmogrifier.sections.folders does a good job
    of creating id-only blank folders for our items. This however,
    fetches the full data on the yet-unseen containers and put them
    in the pipeline. Optionally it can make an
    extensive use of sc.transmogrifier.whitehole to make the containers
    complete the pipeline _before_ the current Item.

    Currently this pipeline depends on another blueprint to consume
    the "__remote_url_fetch" key it puts on new container items
    to actually retrieve that item data. sc.transmogrifier.utils.remotefetcher
    does that, but it is hardwired to a pipeline using collective.jsonmigrator

    """

    def set_options(self):
        self.newPathKey = self.options.get('new-path-key', None)
        self.newTypeKey = self.options.get('new-type-key', '_type')
        self.folderType = self.options.get('folder-type', 'Folder')
        self.cache = self.options.get('cache', 'true').lower() == 'true'

        self.use_wormhole = ast.literal_eval(
                self.options.get("use_wormhole", "False"))
        self.use_original_path = ast.literal_eval(
                self.options.get("use_original_path", "False"))
        self.remote_fetch = ast.literal_eval(
                self.options.get("remote_fetch", "True"))
        self.remote_prefix = self.options.get("remote_prefix", "http://plone.org")

        # blueprint initialization
        self.seen = set()
        self.traverse = self.transmogrifier.context.unrestrictedTraverse

    def __iter__(self):
        self.count_cocoons = 0
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
        """
            Long history short:
            the NITF converter pipeline we are using
            yields the news item (or blogpost, opor wathever)
            and them its image attribute, as a separate
            content, in the same "yield" loop -
            this separate content is yielded before the
            whitehole blueprint is ever reached. (and obviously
            there would be no container for it in this run
            of pipeline loop).
            So we "freeze" the other items here, and just
            let through the things we created ourselves.

            This should actually be a common scenario -
            therefore this have to be factored
            out and made simpler to use.

        """


        # FIXME:
        # Factor this out into whitehole/wormhole blueprint framework


        if COCOON_KEY in item:
            self.count_cocoons -= 1
            logger.info("Unthawning item %s to proceed on the pipeline" %
                        item[COCOON_KEY].get("_path", "<unknown>"))
            return [item[COCOON_KEY]]
        if self.count_cocoons:
            if "__time_traveler" in item:
                # This is one of ours - let it pass!
                item.pop("__time_traveler")
            else:
                wormhole = self.storage["wormhole"]
                #some item scheduled in the pipeline trying to get ahead
                # of our time_travelers!
                # THAT COULD GET OUR GRANDFATHER KILLED!! DELAY IT!
                logger.info("Delaying item %s - it will proceed the pipeline"
                            " when the wormhole queue is emptied" %
                            item.get("_path", "<unknown>"))
                cocoon = {COCOON_KEY: item}
                self.count_cocoons += 1
                # Deques have no insert :-(
                # we have to mangle with space time weaving itself
                position = 0
                while True:
                    if  COCOON_KEY in wormhole[-1]:
                        wormhole.append(cocoon)
                        break
                    position += 1
                    wormhole.rotate(1)
                wormhole.rotate(-position)
                raise ThouShallNotPass

        traverse = self.traverse

        items = []
        path = self.get_path(item)

        newPathKey = self.newPathKey or self.pathkey(*item.keys())[0]
        newTypeKey = self.newTypeKey

        stripped_path = path.strip("/")
        elems = stripped_path.rsplit('/', 1)
        container, id = elems if len(elems) > 1 else ("", elems[0])

        container_path_items = container.split('/')

        original_container_parts = item.get("_orig_path", "").strip("/").split("/")[:-1]

        # This may be a new container
        if container in self.seen or not container_path_items:
            raise NothingToDoHere

        checked_elements = []

        # Check each possible parent folder
        path_exists = True
        for element in container_path_items:
            checked_elements.append(element)
            currentPath = '/'.join(checked_elements)

            if self.cache:
                if currentPath in self.seen:
                    continue
                self.seen.add(currentPath)

            if path_exists and traverse(currentPath, None) is None:
                # Path does not exist from here on
                path_exists = False

            if path_exists:
                continue

            # We don't have this path - yield to create a
            # skeleton folder
            new_folder = {}
            new_folder[newPathKey] = '/' + currentPath
            new_folder[newTypeKey] = self.folderType
            # Set folder to be published if item is to be as well:
            # FIXME - maybe check the "_review_state" key
            # rather than "_transitions" /
            # even further - have a *utils function to ensure
            # proper "_transitons" and "_review_state"
            # from a _workflow_history item key.
            if "_transitions" in item:
                new_folder["_transitions"] = item["_transitions"]

            remote_url = self.remote_prefix.rstrip("/") + "/"
            if self.remote_fetch:
                if self.use_original_path and "_orig_path" in item:
                    # think of it this way:
                    # if item["_orig_path"] == "/vanishing/old/path/item"
                    # and item["_path"] == "/new/path/item"
                    # we need to schedule for fetching
                    # /vanishing/old and /vanishing/old/path from the remote
                    # (there must be some other blueprint to change
                    # /vanishing/old to /new in the pipeline)

                    # following this use case. if element == "new"
                    index =  len(checked_elements) - len(container_path_items)
                    # will yield "-1". we should have
                    # original_container_parts ==["vanishing", "old", "path"]
                    if index == 0: index = None
                    remote_url += \
                        "/".join(original_container_parts[:index]).lstrip("/")
                else:
                    remote_url += currentPath
                # FIXME: should use the transmogrifier
                # mechanism to target these to a specifc
                # blueprint
                new_folder["__remote_url_fetch"] = remote_url
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
            cocoon = {COCOON_KEY: item}
            self.storage["wormhole"].appendleft(cocoon)
            self.count_cocoons += 1
            for new_folder in reversed(items):
                new_folder["__time_traveler"] = True
                self.storage["wormhole"].appendleft(new_folder)



            #And...hyperjump back to the beggining of the pipeline, where
            # our item will be hapily yielded by the whitehole blueprint
            raise ThouShallNotPass

        items.append(item)

        return items
