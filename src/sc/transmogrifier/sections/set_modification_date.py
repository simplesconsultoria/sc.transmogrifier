# coding: utf-8
# Author: Joao S. O. Bueno

from zope.interface import implements, classProvides
from Products.CMFCore.interfaces import ISiteRoot
from Acquisition import aq_parent, aq_inner
from Products.Archetypes.interfaces import IBaseObject
from DateTime.DateTime import DateTime
from Products.CMFCore.utils import getToolByName
import transaction

from sc.transmogrifier import logger
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import normalize_url



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
            if  "modification_date" in item:
                paths_and_dates.append((path, item["modification_date"]))
                yield item; continue

        # Commit newly created objects to  the presistence before proceeding
        logger.info("Start setting modification dates")
        transaction.savepoint(True)
        for counter, (path, modification_date) in enumerate(paths_and_dates):
            obj = context.unrestrictedTraverse(str(path).lstrip('/'), None)
            if obj is None:
                continue

            # HACK: Disable item notification, so that
            # reindexing does not change modification dates
            # (max is used as a no-op function here)
            # see: https://blog.isotoma.com/2011/02/setting-the-modification-date-of-an-archetype-object-in-plone/

            obj.__dict__["notifyModified"] = max
            obj.setModificationDate(DateTime(modification_date))
            context.portal_catalog.reindexObject(obj)
            obj.__dict__.pop("notifyModified", "")

            # We got an exception for ZODB trying to pickle the function
            # in the instance attribute when running a large pipeline.
            #  So, trying to mark the savepoints to avoid commits prior to
            #  the attribute deletion on the previous line.
            if not (counter % 50):
                transaction.savepoint(True)

