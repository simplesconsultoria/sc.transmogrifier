# -*- coding:utf-8 -*-
# Original Author: Leonardo Rochael de Almeida
# Refactored by: Joao S. O. Bueno

import ast

from collective.transmogrifier.utils import defaultMatcher
from plone.app.redirector.interfaces import IRedirectionStorage
from zope.component import queryUtility

from sc.transmogrifier import logger

from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import NothingToDoHere

_marker = object()

@blueprint("sc.transmogrifier.redirector")
class RedirectorBlueprint(BluePrintBoiler):
    """Provides redirection to the original path of a content-item

    When migrating a large site, it is common that items sitting in a
    URL shouldmoe to another section or structure. This automatically
    redirects the original item PATH to the new location -
    provided the original path is in the item The default key is "_orig_path"

    and it can be placed there with the blueprint, configured like this in
    the beggining of a pipeline:

    [orig-path]
    blueprint = collective.transmogrifier.sections.inserter
    key = string:_orig_path
    value = python: item.get('_path', '')
    condition = python: not "_orig_path" in item and "_path" in item

    """


    # TODO: refactor to use the new options system
    def set_options(self):
        self.originalPathKey = defaultMatcher(self.options,
                              'orig-path-key', self.name, 'orig_path')
        self.assure_target_exists = ast.literal_eval(
            self.options.get("assure-target-exists", "True"))
        # If true, the portal path will be pre-pended to the original
        # given path when redirecting
        self.add_portal_name = ast.literal_eval(
            self.options.get("add-portal-name", "True"))

    def pre_pipeline(self):
        self.context = self.transmogrifier.context
        self.seen_count = self.changed_count = 0
        self.redirector = queryUtility(IRedirectionStorage)
        if self.redirector is None:
            logger.error(u'No IRedirectionStorage found, '
                      u'skipping all redirections.')
            self.transmogrify = lambda i: i

    def _prepare_path(self, path):
        #Hack - dropping the first path component, and changing it for the
        # portal path:
        if path.startswith(self.portal_path):
            # nothing to change
            return path
        if not self.add_portal_name:
            path = path.lstrip("/").split("/",1)[-1]

        return self.portal_path + '/' + path.lstrip('/')

    def transmogrify(self, item):
        self.seen_count += 1
        original_path_key = self.originalPathKey(*item.keys())[0]
        if not original_path_key:
            # not enough info
            raise NothingToDoHere
        path = self.get_path(item)
        original_paths = item[original_path_key]

        if isinstance(original_paths, basestring):
            original_paths = [original_paths, ]

        original_paths = [self._prepare_path(p) for p in original_paths]
        if self.assure_target_exists:
            # Bails out if can't retrieve object at item's current path:
            if self.get_object(item, raise_=False) is None:
                logger.warn("Ignoring item at %s - object not created" % path)
                raise NothingToDoHere

        if not path.startswith(self.portal_path):
            path = self.portal_path + "/" +  path.lstrip("/")

        for original_path in original_paths:
            if original_path != path:
                self.redirector.add(original_path, path)

        self.changed_count += 1
        return item

    def post_pipeline(self):
        logger.info("Seen: %s, changed: %s",
                 self.seen_count,
                 self.changed_count,
                 extra=dict(seen_count=self.seen_count,
                            changed_count=self.changed_count))
        print "*" * 500, self.seen_count, self.changed_count
