# coding: utf-8
# Author: Joao S. O. Bueno

from Acquisition import aq_inner
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
import transaction

from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler

from sc.transmogrifier import logger

@blueprint("sc.transmogrifier.utils.set_intid")
class SetIntId(BluePrintBoiler):
    """
    In order to be a target to a related item field, an object has to have
    an "IntId". It  is created by objects created in the GUI, but not for
    objects created with the constructor, updater and reindex blueprints.

    This should be used next to them (after constructor, of course)

    Objetcs that already have an intid are not affectd by this call -
    the inner "intids.register" call just returns the existing
    int_id
    """

    def __iter__(self):
        context = self.transmogrifier.context
        paths = []
        for item in self.previous:
            path = self.get_path(item)
            paths.append(path)
            yield item
        logger.info("Start setting intids")
        transaction.commit()
        for path in paths:
            # retrieve object:
            obj = context.unrestrictedTraverse(str(path).lstrip('/'), None)
            if obj is not None:
                res = set_intid(obj)
                logger.info("intid of %s set to %s" % (obj, res))

def set_intid(obj, patch=True):
    if patch:
        import five.intid.keyreference
        # This is a bogus "verifier" function that does not:
        original_func = five.intid.keyreference.aq_iter
        five.intid.keyreference.aq_iter = lambda obj, *bla, **blabla: [obj]
    intids = getUtility(IIntIds)
    int_id = intids.register(aq_inner(obj))
    if patch:
        five.intid.keyreference.aq_iter = original_func
    return int_id