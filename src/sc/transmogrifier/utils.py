# -*- coding: utf-8 -*-
# Author: João S. O. Bueno

# FIXME: FACTOR THIS OUT TO A SC.TRANSMOGRIFIER.UTILS PACKAGE

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

RELATED_KEY = "_relatedItems"
CONNECTION_NAME = "sc_transmogrifier_wordpress_sql"


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
        #TODO: pré-extract path-key, type-key and the object
        #in a configurable maner prior to calling the
        #transmogrify method
        for item in self.previous:
            try:
                item = self.transmogrify(item)
            except NothingToDoHere:
                pass
            yield item

    def set_options(self):
        """ Override to include options parsing and setting"""
        pass

    def transmogrify(self, item):
        """ override me """
        return item

    def get_path(self, item):
        keys = self.pathkey(*item.keys())
        if not keys[1]:
            raise NothingToDoHere
        path = item[keys[0]]
        if not path:
            raise NothingToDoHere
        return path


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
    elif include_numbers and isinstance(item, Number):
        item = unicode(item)
    return item


def normalize_url(url):
    # remove any acentuated character whcih is possible to remove.
    if isinstance(url, str):
        url = url.decode("utf-8")
    url = unicodedata.normalize("NFKD", url).encode(
            'ASCII', 'ignore').decode("ASCII")
    # Allow only the characters bellow:
    url = re.sub(u"[^a-zA-Z0-9/\-\.]", "-", url)
    # and url 's can't start with an underscore in Plone,
    # neither end with two underscores
    if "/" in url:
        path, id = url.rsplit(u"/", 1)
        url = path + u"/" + id.strip(u"_")
    else:
        url = url.strip(u"_")
    return url


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
