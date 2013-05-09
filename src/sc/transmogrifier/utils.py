# -*- coding: utf-8 -*-
# Author: João S. O. Bueno

import sys
import re
import unicodedata

from numbers import Number

from zope.component import provideUtility
#from zope.interface import implements, classProvides
#from collective.transmogrifier.interfaces import ISection, ISectionBlueprint

# as of 0.8b2, SQLAlchemy is crashimnng no stop
# reverting to pure mysql, just to get tehe job done

# We can even aford for a couple connections
# whenever the pipeline is run :-)  )
#from z3c.sqlalchemy import createSAWrapper
#from z3c.sqlalchemy.util import registerSAWrapper
#from z3c.sqlalchemy.util import getSQLAlchemyWrapper

from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from zope.annotation.interfaces import IAnnotations
from zope.interface.declarations import classImplements
from zope.interface.declarations import directlyProvides

from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from Acquisition import aq_inner

class MetaBluePrint(type):
    """
        Metaclass to make classes that inherit from BluePrintBoiler
        automatically "implements(ISection)" and
        "classProvides(ISectionBlueprint)"
    """
    # TODO: move to a "sc.transmogrifier.utils" package
    def __new__(metacls, name, bases, dct):
        abstract = False
        if "_abstract" in dct:
            del dct["_abstract"]
            abstract = True
        new_class = type.__new__(metacls, name, bases, dct)
        if not abstract:
            classImplements(new_class, ISection)
            directlyProvides(new_class, ISectionBlueprint)
        return new_class


class NothingToDoHere(Exception):
    """
    Raise in the transmogrify method to do nothing to an item
    """
    pass


class ThouShallNotPass(Exception):
    """
    Raise in the transmogrify method to discard an item
    """
    pass


class BluePrintBoiler(object):
    # TODO: move to a "sc.transmogrifier.utils" package
    __metaclass__ = MetaBluePrint
    _abstract = True

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.typekey = defaultMatcher(options, 'type-key', name, 'type',
            ('portal_type', 'Type'))
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.set_options()
        # FIXME: fixed logger key should be made generic.
        self.storage = IAnnotations(transmogrifier
            ).setdefault("sc.transmogrifier.utils.storage", {})
        self.storage["logger"] = []
        self.logger_ = self.storage["logger"]

    def __iter__(self):
        """This can be overriden if
           extra logic is needed, else, it just calls
           self.transmogrify with 'item'
        """

        self.pre_pipeline()
        for item in self.previous:
            try:
                item = self.transmogrify(item)
            except NothingToDoHere:
                pass
            except ThouShallNotPass:
                continue
            yield item

        self.post_pipeline()

    def set_options(self):
        """ Override to include options parsing and setting"""
        pass

    def transmogrify(self, item):
        """ override me """
        return item

    def _get_value(self, item, which):
        # pathkey or typekey + whatever future keys:
        getter = getattr(self, which + "key")
        keys = getter(*item.keys())
        if not keys[1]:
            raise NothingToDoHere
        value = item[keys[0]]
        if not value:
            raise NothingToDoHere
        return value

    def get_path(self, item):
        return self._get_value(item, "path")

    def get_type(self, item):
        return self._get_value(item, "type")

    def pre_pipeline(self):
        pass
    def post_pipeline(self):
        pass



def blueprint(blueprint_name):
   # TODO: move to a "sc.transmogrifier.utils" package
    def deco(cls):
        # misteries of the groks and its interfaces:
        # these two calls here should supress the need of
        # the MetaBluePrint metaclass
        # However, as of Plone 4.2, they have no effect here
        # (the same calls are made from the metaclass' __new__
        # and they work):
        #classImplements(cls, ISection)
        #directlyProvides(cls, ISectionBlueprint)
        provideUtility(cls, name=blueprint_name)
        return cls
    return deco


def promote_to_unicode(item, encoding="utf-8", include_numbers=False):
    if (hasattr(item, "__len__") or hasattr(item, "__iter__")) and \
        not isinstance(item, (str, unicode, dict, set)):
        item = list(item)
    if isinstance(item, list):
        for i, sub_item in enumerate(item):
            item[i] = promote_to_unicode(sub_item, encoding, include_numbers)
    elif isinstance(item, str):
        try:
            item = item.decode(encoding)
        except UnicodeDecodeError:
            sys.stderr.write("Error trying to decode %r from utf-8\n" % item)
            raise
            #item = item.decode(encoding, errors="replace")
    elif isinstance(item, dict):
        for key, value in list(item.items()):
            item[key] = promote_to_unicode(value, encoding, include_numbers)
    elif include_numbers and isinstance(item, Number):
        item = unicode(item)
    return item


def normalize_url(url, strip_chars=True):
    # remove any acentuated character whcih is possible to remove.
    if isinstance(url, str):
        was_unicode = False
        url = url.decode("utf-8")
    else:
        was_unicode = True
    url = unicodedata.normalize("NFKD", url).encode(
            'ASCII', 'ignore').decode("ASCII")

    if strip_chars:
        # Allow only the characters bellow:
        url = re.sub(u"[^a-zA-Z0-9/\-\.\_]", "-", url)
        # and url 's can't start with an underscore in Plone,
        # neither end with two underscores
        if "/" in url:
            path, id = url.rsplit(u"/", 1)
            url = path + u"/" + id.strip(u"_")
        else:
            url = url.strip(u"_")

    if not was_unicode:
        url = url.encode("ASCII")

    return url

def normalize_string(string):
    return normalize_url(string, strip_chars=False)

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
