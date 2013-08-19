# -*- coding: utf-8 -*-
# Author: João S. O. Bueno

import ast
from pprint import pformat
import re
import sys
import unicodedata

from numbers import Number

from zope.component import provideUtility
from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from zope.annotation.interfaces import IAnnotations
from zope.interface.declarations import classImplements
from zope.interface.declarations import directlyProvides

from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from Acquisition import aq_inner

from sc.transmogrifier import logger

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
    """Base class for creating blueprints

    features tons of niceties. When looking at transmogrifier blueprints
    in other packages the first thing one perceives is a lot of recurring code -
    to retrieve the path key, the item corresponding object
    if it is already comitted - and even the __iter__ method itself,
    since the goodies are nested an uneeded degree within
     the generator "for" loop.

     This and the related code ains to make creating a new blueprint
     as simple a task as possible - just decorate the class with
     the "blueprint" decorator and mark this as the base class
     (both things are needed due to the way grok works)

     Then, for the simplest cases, just override the "transmogrify"
     method. Use "self.get_path(item)", self.get_type(item) and
     "self.get_object(item)" to properly retrieve these data, or have
     your blueprint gracefully bypassed, as these methods raise a
     'NothingToHere'exception - the pipeline just goes on.

     Also, raise NothingToDohere if upon inspecting an item your find out
     no actions are to be taken, and raise "ThouShallNotPass" if you
     find out an item should be removed from the pipeline altogether

     You can declare an "OPTIONS" class-attibute, consiting of a list
     of tuples to define the configuration parameters
     of your blueprint..

     For each item in the OPTIONS, the first element is used
     as the option element (and the corresponding attribute is set
     on the object when the pipeline is running) - also the option with
     this name  can be overriden in the pipeline .cfg file (either as is,
     or using "-"s instead of "_"s)

     Other interesting methods to be overriden are "pre_pipeline"  and
     "post_pipeline" they are run before and after all items in
     "self.previous" are runthough the pipeline. Usefull things there,
     are, for examle, creation of specialized loggers (which record,say just
     an item's Path to a txt file) and other  acountant stuff.

     Also "self.storage" is a dictionarylike attribute wich stores it's
     data the proper way in the transmgrifier's annotations. It is a nice
     way of passing data in parallell to the pipeline to other blueprints.


    """

    __metaclass__ = MetaBluePrint
    _abstract = True

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.portal_path = make_path(transmogrifier.context)
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

    OPTIONS = ()

    def set_options(self):
        """Scans the class "OPTIONS" attribute for blueprint options

         Set the options as a list of 1, 2,  3- or 4-tuple
         with each option: name, default_value, and
         type - one of "string"(default), "literal" and
         documentation string
         TODO: generate blueprint docs from option docs.

         Each "_" on the option name will accept either "_" or "-"
         literals in the transmogrifier.cfg  file
         """

        options = self.__class__.OPTIONS

        # Normalize options withdefault values:
        options = [(opt[0], None, "string", "") if len(opt) == 1 else
                   (opt[0], opt[1], "string", "") if len(opt) == 2 else
                   (opt[0], opt[1], opt[2], "") if len(opt) == 3 else
                   (opt[0], opt[1], opt[2], opt[3])
                                                 for opt in options]
        set_options = {}
        for name, default, type_, doc in options:
            value = self.options.get(name,
                self.options.get(name.replace("_", "-"), default))
            if type_ == "literal" and isinstance(value, basestring):
                value = ast.literal_eval(value)
            set_options[name] = value
        logger.info("Transmogrifier section %s configured with options:\n %s"
            % (self.name, pformat(set_options)))

        for opt_name, value in sorted(set_options.items()):
            if hasattr(self, opt_name):
                logger.error("Attention: Blueprint object in "
                    "section %s already has an attribute named %s - "
                    "overriding with option value %s - but this is "
                    "probably broken" % (self.name, opt_name, value))
            setattr(self, opt_name, value)


    def transmogrify(self, item):
        """ override me """
        return item

    def _get_value(self, item, which, raise_=True):
        # pathkey or typekey + whatever future keys:
        getter = getattr(self, which + "key")
        keys = getter(*item.keys())
        if not keys[1]:
            if raise_:
                raise NothingToDoHere
            return None
        value = item[keys[0]]
        if not value:
            if raise_:
                raise NothingToDoHere
            return None
        return value

    def get_path(self, item, raise_=True):
        return self._get_value(item, "path")

    def get_type(self, item, raise_=True):
        return self._get_value(item, "type")

    def pre_pipeline(self):
        pass

    def post_pipeline(self):
        pass

    def get_object(self, item, raise_=True):
        path = self.get_path(item)
        if path.startswith("/") and not path.startswith(self.portal_path):
            path = self.portal_path + path
        obj = self.transmogrifier.context.unrestrictedTraverse(path, None)
        # Weed out implicit Acquisition
        if not obj:
            if raise_:
                raise NothingToDoHere
            else:
                return None
        actual_path = make_path(obj)
        if obj is not None and (actual_path != path and
            actual_path !=  self.portal_path + "/" + path.strip("/")):
            obj = None
        if obj is None and raise_:
            raise NothingToDoHere
        return obj

def blueprint(blueprint_name):
    """Class decorator for defining blueprints

    With this in place, one at once declares the blueprint name
    before the code  - instead of having to call
    "zope.component.provideUtility(<myclass>, "blueprint.name")
    after the class declaration. (Gone are the days of Python 2.3
    when there where no decorators)
    """
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


def make_path(obj):
    """Most used pattern in Plone to create the path to a content-item
    """
    return '/'.join(obj.getPhysicalPath())

def promote_to_unicode(item, encoding="utf-8", include_numbers=False):
    """Seamlessly decodes all byte-strings in a data-structure to unicode

    Walk nested struvtures with unicode-strings/byte-strings/tuples/
    lists/dicts and promotes all found strings in a safe-way to unicode.
    Setting "include numbers" will render any Number found to an
    unicode decimal representation of it.

    """
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
    """Removes any acentuated character which is possible to remove

    Other invalid URL chars are silently replaced by "-"
    """

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

# XXX: Refactor somewhere else
def transition_from_history(item, target_workflow="simple_publication_workflow"):
    """Parses the "_workflow_history"  item entry for the final object state"

    """
    # Add hoc fix due to attributing the "workflow_history"
    # to the object not working for the final workflow state
    # of dexterity types
    # In time: the correct fix would involve debugging why
    # setting the workflow_history to the item does not publish it,
    # (See collective.jsonmigrator.workflowhistory blueprint -
    # but its buggy and skipping dexterity contents right now.
    # making it not skip the item, does no better to publish it
    # either)

    """
    Sample _workflow_history entry:
    "_workflow_history": {"simple_publication_workflow":
    [{"action": null, "review_state": "private",
     "actor": "admin", "comments": "",
     "time": "2012/03/01 14:38:38.585 GMT-3"},
     {"action": "publish", "review_state": "published",
     "actor": "admin", "comments": "",
     "time": "2012/03/01 14:38:39.572 GMT-3"}]}
    """
    if ("_workflow_history" in item and
             target_workflow in item["_workflow_history"]):
        transitions = (item["_workflow_history"]
            [target_workflow])
        if transitions[-1]["review_state"] == "published":
            item["_transitions"] = "publish"
            # Since we are at it, pick the "published date"
            # to the datefixer blueprint, just in case:
            published = transitions[-1].get("time", "")
            if published:
                item["_published_date"] = published.split()[0]

    return item
