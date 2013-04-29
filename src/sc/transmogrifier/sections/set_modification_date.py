# coding: utf-8
# Author: Joao S. O. Bueno

from DateTime.DateTime import DateTime
from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler

import transaction


@blueprint("sc.transmogrifier.utils.set_modification_date")
class SetModificationDate(BluePrintBoiler):

    def __iter__(self):
        context = self.transmogrifier.context
        paths_and_dates = []

        for item in self.previous:
            # retrieve object:
            pathkey = self.pathkey(*item.keys())[0]
            if not pathkey:
                yield item; continue
            path = item[pathkey]
            #obj = context.unrestrictedTraverse(str(path).lstrip('/'), None)
            if "modification_date" in item:
                paths_and_dates.append((path, item["modification_date"]))
            yield item

        # Commit newly created objects to the persistence before proceeding
        transaction.savepoint(True)
        logger.info("Start setting modification dates")

        for counter, (path, modification_date) in enumerate(paths_and_dates):
            obj = context.unrestrictedTraverse(str(path).lstrip('/'), None)
            if obj is None:
                continue

            # HACK: Disable item notification, so that
            # reindexing does not change modification dates
            # (max is used as a no-op function here)
            # see: https://blog.isotoma.com/2011/02/setting-the-modification\
            # -date-of-an-archetype-object-in-plone/

            obj.__dict__["notifyModified"] = max
            obj.setModificationDate(DateTime(modification_date))
            obj.reindexObject(idxs=["modified"])
            obj.__dict__.pop("notifyModified", "")

            logger.info("Mod date of %s set to %s" % (path, modification_date))
            # We got an exception for ZODB trying to pickle the function
            # in the instance attribute when running a large pipeline.
            #  So, trying to mark the savepoints to avoid commits prior to
            #  the attribute deletion on the previous line.
            if not (counter % 50):
                transaction.savepoint(True)
