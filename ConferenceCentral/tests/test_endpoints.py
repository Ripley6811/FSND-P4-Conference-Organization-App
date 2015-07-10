import unittest
import json

from google.appengine.api import urlfetch
from google.appengine.ext import testbed
from google.appengine.api.app_identity import get_default_version_hostname

from models import Conference


# WARNING: Make sure app is set up with a mocked login authorization
# to test endpoints
class EndpointsTestCase(unittest.TestCase):
    #### SET UP and TEAR DOWN ####
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
#        self.testbed.init_user_stub()  # Doesn't seem to do anything
        # The following two stubs (seem to) create a test datastore
        # and routes the app endpoints to the test datastore
#        self.testbed.init_urlfetch_stub()  # !!RECURSION DEPTH EXCEEDED
        self.testbed.init_app_identity_stub()  # Routes to test datastore
        self.testbed.init_datastore_v3_stub()  # Creates test datastore
        self.urlbase = 'http://' + get_default_version_hostname()

    def tearDown(self):
        self.testbed.deactivate()

    #### TESTS ####
    def testHomepageAndNopageReturns(self):
        response = urlfetch.fetch('http://localhost:8080')
        self.assertEqual(response.status_code, 200)
        response = urlfetch.fetch('http://localhost:8080/monkey')
        self.assertEqual(response.status_code, 404)

    def testCreateConference_BadRequest(self):
        url = 'http://localhost:8080/_ah/api/conference/v1/conference'
        params = {}
        response = urlfetch.fetch(url,
                        payload=json.dumps(params),
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 400)

    def testCreateConference(self):
        url = 'http://localhost:8080/_ah/api/conference/v1/conference'
        params = {'name':'BAAAA Conference'}
        self.assertEqual(0, len(Conference.query().fetch(5)))
        response = urlfetch.fetch(url, 
                        payload=json.dumps(params),
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(1, len(Conference.query().fetch(5)))
        self.assertEqual(Conference.query().get().name, params['name'])

    def testProfile(self):
        url = 'http://localhost:8080/_ah/api/conference/v1/profile'
        res = urlfetch.fetch(url, method='GET')
        self.assertEqual(res.status_code, 200)
        self.assertIn('@', json.loads(res.content)['mainEmail'])

    def test_getConferencesCreated(self):
        url = '/_ah/api/conference/v1/getConferencesCreated'
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(Conference.query().fetch(5)), 0)
