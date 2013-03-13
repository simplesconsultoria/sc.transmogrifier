# -*- coding:utf-8 -*-
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher
from logging import getLogger
from plone.app.redirector.interfaces import IRedirectionStorage
from zope.component import queryUtility
from zope.interface import classProvides
from zope.interface import implements

_marker = object()
log = getLogger(__name__)


class RedirectorBlueprint(object):

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.name = name
        self.pathKey = defaultMatcher(options, 'path-key', name, 'path')
        self.originalPathKey = defaultMatcher(options, 'orig-path-key', name,
                                              'orig_path')
        self.seen_count = self.changed_count = 0
        self.portal_path = '/'.join(self.context.getPhysicalPath())

        self.redirector = queryUtility(IRedirectionStorage)
        if self.redirector is None:
            log.error(u'No IRedirectionStorage found, '
                      u'skipping all redirections.')

    def _prepare_path(self, path):
        return self.portal_path + '/' + path.encode().lstrip('/')

    def getObject(self, path):
        obj = self.context.unrestrictedTraverse(path, None)
        # Weed out implicit Acquisition
        if obj is not None and '/'.join(obj.getPhysicalPath()) != path:
            log.warn("Ignoring %r: path doesn't match %r", obj, path)
            return None
        return obj

    def transmogrify(self, item):
        if self.redirector is None:
            return
        path_key = self.pathKey(*item.keys())[0]
        original_path_key = self.originalPathKey(*item.keys())[0]
        if not (path_key and original_path_key):
            # not enough info
            return

        path = self._prepare_path(item[path_key])
        original_path = item[original_path_key]

        if isinstance(original_path, (str, unicode)):
            original_path = [original_path, ]

        original_path = [self._prepare_path(p) for p in original_path]
        obj = self.getObject(path)
        if obj is None:
            # path doesn't exist
            return

        for item in original_path:
            self.redirector.add(item, path)
        self.changed_count += 1

    def __iter__(self):
        for item in self.previous:
            self.seen_count += 1
            self.transmogrify(item)
            yield item
        log.info("Seen: %s, changed: %s", self.seen_count, self.changed_count,
                 extra=dict(seen_count=self.seen_count,
                            changed_count=self.changed_count,))
