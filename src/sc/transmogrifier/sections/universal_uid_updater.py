# coding: utf-8
# Author: Joao S. O. Bueno

from Products.Archetypes.interfaces import IReferenceable as\
                                                 ATIReferenceable
from Products.Archetypes.config import UUID_ATTR as AT_UID_ATTR
from plone.app.referenceablebehavior.referenceable import IReferenceable as\
                                                         DXIReferenceable

from plone.uuid.interfaces import ATTRIBUTE_NAME as DX_UID_ATTR

from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import ThouShallNotPass, NothingToDoHere


@blueprint("sc.transmogrifier.universal_uid_updater")
class UniversalUIDUpdater(BluePrintBoiler):
    """
    The UID blueprint in collective.transmogrifier
    can't deal withdexterity content.

    Other possible exiting blueprints can't deal with
    ATContent.
    One Blueprint to UID-up them all
    """

    OPTIONS = [("uidkey", "_uid", "string")]

    def transmogrify(self, item):
        path = self.get_path(item)
        obj = self.get_object(item)

        uid = item.get(self.uidkey, "")
        if not uid:
            raise NothingToDoHere

        at_uid = ATIReferenceable.providedBy(obj)
        dx_uid = DXIReferenceable.providedBy(obj)
        if at_uid or dx_uid:
            old_uid = obj.UID()
            if old_uid != uid:
                # Code from plone.app.transmogrifier used for AT objects:
                if at_uid:
                    if not old_uid:
                        setattr(obj, AT_UUID_ATTR, uid)
                    else:
                        obj._setUID(uid)
                elif dx_uid:
                    setattr(obj, DX_UID_ATTR, uid)
        return item


"""
Fo checkign and setting the UID in dexterity items,
the following quiestions in stackoverflow where consulted:

http://stackoverflow.com/questions/17425668/plone-dexterity-behaviors-referenceablebehavior-not-referenceable
http://stackoverflow.com/questions/14955747/set-uid-for-dexterity-type
"""