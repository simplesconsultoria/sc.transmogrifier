# -*- coding:utf-8 -*-



from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher
from logging import getLogger
from plone.app.redirector.interfaces import IRedirectionStorage
from zope.component import queryUtility
from zope.interface import classProvides
from zope.interface import implements

from sc.transmogrifier import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import NothingToDoHere

_marker = object()
log = getLogger(__name__)

@blueprint("sc.transmogrifier.redirector")
class RedirectorBlueprint(BluePrintBoiler):

    def set_options(self):
        self.pathKey = defaultMatcher(self.options, 'path-key', name, 'path')
        self.originalPathKey = defaultMatcher(self.options,
                                        'orig-path-key', name, 'orig_path')

    def pre_pipeline(self):
        self.context = self.transmogrifier.context
        self.seen_count = self.changed_count = 0
        self.portal_path = '/'.join(self.context.getPhysicalPath())
        self.redirector = queryUtility(IRedirectionStorage)
        if self.redirector is None:
            logger.error(u'No IRedirectionStorage found, '
                      u'skipping all redirections.')
            self.transmogrify = lambda(s, i): i

    def _prepare_path(self, path):
        return self.portal_path + '/' + path.encode().lstrip('/')

    def transmogrify(self, item):
        self.seen_count += 1
        original_path_key = self.originalPathKey(*item.keys())[0]
        if not original_path_key:
            # not enough info
            raise NothingToDoHere

        path = self.get_path(item)
        original_path = item[original_path_key]

        if isinstance(original_path, basestring):
            original_path = [original_path, ]

        original_path = [self._prepare_path(p) for p in original_path]
        obj = self.get_object(item)

        for item in original_path:
            self.redirector.add(item, path)
        self.changed_count += 1
        return item

    def post_pipeline(self):
        logger.info("Seen: %s, changed: %s",
                 self.seen_count,
                 self.changed_count,
                 extra=dict(seen_count=self.seen_count,
                            changed_count=self.changed_count))
