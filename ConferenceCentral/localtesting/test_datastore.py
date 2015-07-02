import unittest
import json
import urllib, urllib2

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext.db import BadValueError
from google.appengine.ext import testbed

#from main import app
from conference import endpoints
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


class EndpointsTestCase(unittest.TestCase):
    #### SET UP and TEAR DOWN ####
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
#        self.testbed.init_urlfetch_stub()

    def tearDown(self):
        self.testbed.deactivate()

    #### METHODS ####
    def loginUser(self, email='python.photography@gmail.com', id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    #### TESTS ####
    def testLogin(self):
        self.assertFalse(users.get_current_user())
        self.loginUser()
        self.assertTrue(users.get_current_user().email() == 'python.photography@gmail.com')
        self.loginUser(is_admin=True)
        self.assertTrue(users.is_current_user_admin())

    def testHomepageAndNopageReturns(self):
        response = urlfetch.fetch('http://localhost:8080')
        self.assertEquals(response.status_code, 200)
        response = urlfetch.fetch('http://localhost:8080/monkey')
        self.assertEquals(response.status_code, 404)

    def testCreateConference_Unauthorized(self):
        url = 'http://localhost:8080/_ah/api/conference/v1/conference'
        params = json.dumps({'name':'GAE Testing Conference'})
        response = urlfetch.fetch(url,
                        payload=params,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEquals(response.status_code, 401)

#    def testCreateConference_BadRequest(self):
##        self.loginUser()
#        authreq_data = urllib.urlencode({'email': 'user@example.com',
#                                         'continue': '',
#                                         'action': 'Login'})
#        login_uri = ('http://localhost:8080/_ah/login?' + authreq_data)
#        res = urlfetch.fetch(login_uri)
#        self.assertEquals(res.status_code, 200)
#
#        url = 'http://localhost:8080/_ah/api/conference/v1/conference'
#        params = json.dumps({'name':'GAE Testing Conference'})
#        response = urlfetch.fetch(url,
#                        payload=params,
#                        method=urlfetch.POST,
#                        headers={'Content-Type': 'application/json'})
#        self.assertEquals(response.status_code, 400)

#    def testCreateConference(self):
#        authreq_data = urllib.urlencode({'email': 'user@example.com',
##                                         'continue': '',
#                                         'action': 'Login'})
#        login_uri = (users.create_login_url() + '&' + authreq_data)
#        res = urlfetch.fetch(users.create_login_url())
##        self.loginUser()
#        self.assertEquals(res.status_code, 200)
#
#        url = 'http://localhost:8080/_ah/api/conference/v1/conference'
#        params = json.dumps({'name':'GAE Testing Conference'})
#        response = urlfetch.fetch(url,
#                        payload=params,
#                        method=urlfetch.POST,
#                        headers={'Content-Type': 'application/json'})
#        self.assertEquals(response.status_code, 200)

    def testProfile(self):
        authreq_data = urllib.urlencode({'email': 'python.photography@gmail.com'})
#                                         'continue': '',
#                                         'action': 'Login'})
        url = 'http://localhost:8080/_ah/api/conference/v1/profile'
        login_uri = 'http://localhost:8080/_ah/login?email=python.photography@gmail.com&admin=True&action=Login' #+ '&' + authreq_data
        res = urlfetch.fetch(users.create_login_url()+'?email=python.photography@gmail.com', follow_redirects=False)
        self.loginUser()
        self.assertEquals(res.status_code, 302)
        self.assertTrue(users.get_current_user().email() == 'python.photography@gmail.com')
#        self.assertEquals(res.headers, 200)
#        dal = res.headers['Set-Cookie']
#        res = urlfetch.fetch(login_uri)
#        self.assertEquals(login_uri, 200)
#        self.loginUser()
#        self.assertTrue(users.get_current_user().email() == 'python.photography@gmail.com')
        res = urlfetch.fetch(url, method='GET')
        self.assertEquals(res.status_code, 200)
