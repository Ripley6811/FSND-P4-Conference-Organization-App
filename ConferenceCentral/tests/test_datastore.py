import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext.db import BadValueError
from google.appengine.ext import testbed

from models import Conference
from models import Session
from datetime import date, time


class DatastoreTestCase(unittest.TestCase):
    #### SET UP and TEAR DOWN ####
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

    #### TESTS ####
    def test_new_conference_fails(self):
        with self.assertRaises(BadValueError):
            Conference().put()

    def test_new_session_fails(self):
        with self.assertRaises(BadValueError):
            Session().put()

    def test_new_conference(self):
        Conference(name='Test').put()
        self.assertEqual(1, len(Conference.query().fetch(2)))

    def test_new_session(self):
        Session(name='TestSess', date=date(2015,1,2), startTime=time(7), conferenceKey='test').put()
        self.assertEqual(1, len(Session.query().fetch(2)))
