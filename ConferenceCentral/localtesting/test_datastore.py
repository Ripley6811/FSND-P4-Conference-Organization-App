import sys
#sys.path.insert(1, 'C:\\Program Files (x86)\\Google\\google_appengine')
#sys.path.insert(1, 'C:\\Program Files (x86)\\Google\\google_appengine\\lib\\yaml\\lib')
#sys.path.insert(1, 'google-cloud-sdk/platform/google_appengine')
#sys.path.insert(1, 'google-cloud-sdk/platform/google_appengine/lib/yaml/lib')
#sys.path.insert(1, '..')

import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from models import Conference


class DatstoreTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        # Clear ndb's in-context cache between tests.
        # This prevents data from leaking between tests.
        # Alternatively, you could disable caching by
        # using ndb.get_context().set_cache_policy(False)
        ndb.get_context().clear_cache()

    def tearDown(self):
        self.testbed.deactivate()

    def test_new_conference(self):
        Conference(name='Test').put()
        self.assertEqual(1, len(Conference.query().fetch(2)))

if __name__ == '__main__':
    unittest.main()
