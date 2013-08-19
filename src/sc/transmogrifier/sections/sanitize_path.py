# coding: utf-8
# Author: Joao S. O. Bueno

from zope.interface import implements, classProvides
from Products.CMFCore.interfaces import ISiteRoot
from Acquisition import aq_parent, aq_inner

from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import normalize_url


# Plan B:  - duplicate the code from
# Products.CMFCOre.PortalFolder.PortalFolderBase._CheckId

def get_plone_root(ctx):
    obj = aq_inner(ctx)
    while obj is not None:
        if ISiteRoot.providedBy(obj):
            break
        obj = aq_parent(obj)
    return obj

@blueprint("sc.transmogrifier.utils.sanitize_path")
class SanitizePath(BluePrintBoiler):
    """Cleans up IDs and Paths keeping information about the changes

        Remove strange charaters or otherwise
        invalid ID and paths that would make Plone explode;
        Creates a transmogrifier-wide "changed PATH" attributes
        so that other sections can find proper references to what has changed

        TODO: add an option to scan the "text" field of content types
        and normalize relative URLs in "src" and "href" references
        so that imported items and references to them are kept in sync!

    """

    def __iter__(self):
        for item in self.previous:

            id = item.get("id", u"")
            pathkey = self.pathkey(*item.keys())[0]
            if not pathkey:
                yield item; continue
            path = item[pathkey]
            _id = path.rstrip("/").rsplit("/")[-1]
            if not id:
                id = _id

            # Removes accented characters from composed characters
            # where possible - and supress non "alphanum_-" chars:
            # (example: u"maçã" -> u"maca"
            normal_path = path.rstrip("/").rsplit("/",1)[0]  + \
                          "/" + normalize_url(_id)
            normal_id = normalize_url(id)

            plone = get_plone_root(self.transmogrifier.context)
            if plone:
                s_id = str(normal_id)
                if (hasattr(plone, s_id) and
                    s_id not in plone.contentIds()):
                    # This condition would raise a "BadRequest"
                    # exception
                    normal_id += u"_1"
                    normal_path += u"_1"
            if normal_path == path and normal_id == id:
                yield item
                continue
            if "id" in item:
                item["id"] = normal_id
            item[pathkey] = normal_path
            if not hasattr(self.transmogrifier, "sc_transmogrifier_changed_paths"):
                self.transmogrifier.sc_transmogrifier_changed_paths = {}
            self.transmogrifier.sc_transmogrifier_changed_paths[path] = normal_path
            if not "_orig_path" in item:
                item["_orig_path"] = normal_path
            yield item

