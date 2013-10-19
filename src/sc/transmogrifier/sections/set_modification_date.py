# coding: utf-8
# Author: Joao S. O. Bueno

from DateTime.DateTime import DateTime
from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler

import transaction


@blueprint("sc.transmogrifier.utils.set_modification_date")
class SetModificationDate(BluePrintBoiler):
    """Restores/sets cration and modification dates

    When performing a migration it is needed to keep the last
    modificati0on date of a content item - by default,
    what happens is that the timestamp of the import pipleine-run
    is set as modification - and even creation - date for all objects;

    This sets the modification and creation date for those on
    the proper fields on the item - working around plone tendency
    to not allow one to set the mod. date.
    """
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
            if "modification_date" or "creation_date" in item:
                paths_and_dates.append((path, item.get("modification_date", ""),
                                        item.get("creation_date", "")))
            yield item

        # Commit newly created objects to the persistence before proceeding
        transaction.savepoint(True)
        logger.info("Start setting modification dates")

        for counter, (path, modification_date, creation_date) in \
                                             enumerate(paths_and_dates):
            obj = context.unrestrictedTraverse(str(path).lstrip('/'), None)
            if obj is None:
                continue
            if not creation_date and not obj.creation_date:
                creation_date = modification_date


            idx = []
            if modification_date:
                obj.setModificationDate(DateTime(modification_date))
                logger.info("Modification date of %s set to %s" %
                          (path, modification_date))
                idx.append("modified")

            if creation_date:
                obj.creation_date = DateTime(creation_date)
                logger.info("Creation date of %s set to %s" %
                            (path, creation_date))
                idx.append("created")

            if not obj.effective_date:
                obj.effective_date = obj.creation_date
                idx.append("effective")

            obj.reindexObject(idxs=idx)

            if not (counter % 50):
                transaction.savepoint(True)

            ## HACK: Disable item notification, so that
            ## reindexing does not change modification dates
            ## (max is used as a no-op pickable function here -
            ##  it is plain python "max" - kin to "min" )
            ## see: https://blog.isotoma.com/2011/02/setting-the-modification\
            ## -date-of-an-archetype-object-in-plone/

            ## FIXME: still does not work if run from an interactive
            ## instance debug mode :-(

            #obj.__dict__["notifyModified"] = max
            #if modification_date:
                #obj.setModificationDate(DateTime(modification_date))
                #logger.info("Modification date of %s set to %s" %
                          #(path, modification_date))
            #if creation_date:
                #obj.creation_date = DateTime(creation_date)
                #logger.info("Creation date of %s set to %s" %
                            #(path, creation_date))
            #obj.reindexObject(idxs=["modified", "created"])
            #obj.__dict__.pop("notifyModified", "")


