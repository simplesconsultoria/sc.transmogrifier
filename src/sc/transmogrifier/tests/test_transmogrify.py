import os.path
import sys
import logging.handlers
from unittest import TestCase

from zope.interface import classProvides, implements
from zope.component import (
    provideUtility,
    queryUtility,
    getUtility,
    ComponentLookupError,
)
from zope.site.hooks import getSiteManager
from zope.configuration import xmlconfig
from plone.app.redirector.interfaces import IRedirectionStorage
from plone.testing import z2
from plone.app.testing import (
    PLONE_FIXTURE,
    SITE_OWNER_NAME,
    PloneSandboxLayer,
    IntegrationTesting,
)
from collective.transmogrifier.interfaces import ISectionBlueprint, ISection
from collective.transmogrifier.sections.tests import SampleSource

OLD_NAME = 'oldPath'
NEW_NAME = 'newPath'
TEST_SOURCE = u'sc.transmogrifier.tests.redirectorsource'
TEST_PIPELINE_CONFIG = u"sc.transmogrifier.tests.pipeline"
TESTS_FOLDER = unicode(os.path.dirname(__file__), sys.getfilesystemencoding())
SOURCE_SAMPLE = (
    dict(_path='/' + NEW_NAME,
         _type='Folder',
         _orig_path='/' + OLD_NAME,
    ),
    # element without `_path`, should be ignored
    dict(_type='Folder',
         _orig_path='/someOrigPath',
    ),
    # element without `_orig_path`, should be ignored
    dict(_path='/somePath',
         _type='Folder',
    ),
)

# provide a simple source for just the redirector tests
class TestSource(SampleSource):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, *args, **kw):
        super(TestSource, self).__init__(*args, **kw)
        self.sample = SOURCE_SAMPLE

class TransmogrifyRedirectorLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import sc.transmogrifier
        xmlconfig.file('configure.zcml',
                       sc.transmogrifier, context=configurationContext)
        import collective.transmogrifier
        xmlconfig.file('configure.zcml',
                       collective.transmogrifier, context=configurationContext)

        provideUtility(TestSource,
                       name=TEST_SOURCE)
        from collective.transmogrifier.meta import configuration_registry
        configuration_registry.registerConfiguration(
            name=TEST_PIPELINE_CONFIG,
            title=u"Example pipeline configuration",
            description=u"This is an example pipeline configuration",
            configuration=os.path.join(TESTS_FOLDER, u"pipeline.cfg")
        )

TRANSMOGRIFY_REDIRECTOR_FIXTURE = TransmogrifyRedirectorLayer()
TRANSMOGRIFY_REDIRECTOR_INTEGRATION_LAYER = IntegrationTesting(
    bases=(TRANSMOGRIFY_REDIRECTOR_FIXTURE, ),
    name="TransmogrifyRedirector:Integration",
)

class TestTransmogrify(TestCase):

    layer = TRANSMOGRIFY_REDIRECTOR_INTEGRATION_LAYER

    def setUp(self):
        super(TestTransmogrify, self).setUp()
        self.redirector = getUtility(IRedirectionStorage)
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        z2.login(self.app['acl_users'], SITE_OWNER_NAME)
        portal_path = '/'.join(self.portal.getPhysicalPath())
        self.old_path = portal_path + '/' + OLD_NAME
        self.new_path = portal_path + '/' + NEW_NAME
        # capture all the logs of the pipeline section
        self.handler = logging.handlers.BufferingHandler(sys.maxint)
        from sc.transmogrifier.redirector import log
        log.addHandler(self.handler)
        self._old_log_level = log.level
        log.setLevel(1)

    def tearDown(self):
        from sc.transmogrifier.redirector import log
        log.removeHandler(self.handler)
        self.handler.flush()
        log.level = self._old_log_level
        super(TestTransmogrify, self).tearDown()

    def transmogrify(self):
        from collective.transmogrifier.transmogrifier import Transmogrifier
        transmogrifier = Transmogrifier(self.portal)
        transmogrifier(TEST_PIPELINE_CONFIG)        
        # RedirectorBlueprint logs the final count of seen and changed objects:
        final_log = [
            log_record for log_record in self.handler.buffer
            # c.f.: RedirectorBlueprint.__iter__():
            if getattr(log_record, 'changed_count', None) is not None
        ][-1]
        self.assertEqual(final_log.seen_count, len(SOURCE_SAMPLE))
        return final_log

    def test_transmogrify_no_content(self):
        self.transmogrify()
        # Since we don't have any content that matches the records in
        # the pipeline, no redirection should be set up:
        self.assertEqual(len(list(self.redirector)), 0)

    def test_transmogrify(self):
        # create a piece of content to pretend it was imported with the pipeline
        self.portal.invokeFactory('Folder', NEW_NAME)
        # now there should be one redirection:
        self.transmogrify()
        self.assertEqual(len(list(self.redirector)), 1)

    def test_no_IRedirectionStorage(self):
        self.assertEqual(len(list(self.redirector)), 0)
        # create a piece of content to pretend it was imported with the pipeline
        self.portal.invokeFactory('Folder', NEW_NAME)
        # let's unregister the redirector:
        getSiteManager().unregisterUtility(provided=IRedirectionStorage)
        self.assertRaises(ComponentLookupError, getUtility, IRedirectionStorage)
        # This should not fail:
        self.transmogrify()
        # and obviously no redirection should be set-up:
        self.assertEqual(len(list(self.redirector)), 0)
