# coding: utf-8
# Author: Joao S. O. Bueno

from collections import deque

from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler


class Wormhole(deque):
    def iterpop(self):
        while True:
            try:
                yield self.popleft()
            except IndexError:
                break

    push = deque.append

@blueprint("sc.transmogrifier.utils.whitehole")
class Whitehole(BluePrintBoiler):
    """Inserts an item discovered later in the beggning of the pipeline

       It is not uncommon to "unearth" related content items, like
       folder, imagesm and so on - that are retrieved form the values
       in an item already traversing the pipeline. These otehr items
       should traverse all the pipeline steps, not only the steps
       ahead of the point they where isolated.
       Instead of yielding these items late on the pipeline, do
       self.transmogrifier.storage["wormhole"].push(other_item)
       and it will be inserted in the pipeline ahead of items
       from the other sources

       TODO: there is a complicated handling that can be used
       to insert the related items _before_ the currently
       running item. Plans are to add some options
       to make this simpler - currently the
       sc.transmogrifier.utils.migration_folders makes use
       of this pattern

       Just put this blueprint early on the pipeline, after
       any other source blueprints,

       Push an item in a list into the transmogrifiers
       self.storage["wormhole"] entry,
       in any later blueprint, to have it re-surface
       from here!
       (self.storage is defined as a transmogrifier object
        anotation in the Boilerplate base class)

    """


    def __init__(self, *args, **kw):
        super(Whitehole, self).__init__(*args, **kw)
        self.storage["wormhole"] = Wormhole()
    def __iter__(self):
        for item in self.previous:
            for time_traveler in self.storage["wormhole"].iterpop():
                logger.info("Item %s emerged from the entrails of "
                    "Deep Space" % time_traveler.get("_path",u"<unknown>"))
                yield time_traveler
            yield item
        for time_traveler in self.storage["wormhole"].iterpop():
            logger.info("Item %s emerged from the entrails of "
                 "Deep Space, even as the Universe collapses!"
                  % time_traveler.get("_path",u"<unknown>"))
            yield time_traveler