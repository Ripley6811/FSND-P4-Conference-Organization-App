import unittest
import json

from google.appengine.api import urlfetch
from google.appengine.ext import testbed
from google.appengine.api import modules
from google.appengine.api.app_identity import get_default_version_hostname

from models import Conference


# Deployed app tests
# Test that endpoints return appropriate no-login status codes on deployed app
class DeployedAuthorizationTestCase(unittest.TestCase):
    #### SET UP and TEAR DOWN ####
    def setUp(self):
        self.urlbase = 'https://' + get_default_version_hostname()

    #### TESTS ####
    def testHomepageAndNopageReturns(self):
        res = urlfetch.fetch(self.urlbase)
        self.assertEqual(res.status_code, 200)
        res = urlfetch.fetch(self.urlbase + '/monkey')
        self.assertEqual(res.status_code, 404)

    def test_createConference(self):
        url = '/_ah/api/conference/v1/conference'
        res = urlfetch.fetch(self.urlbase + url,
                             payload=json.dumps({}),
                             method=urlfetch.POST,
                             headers={'Content-Type': 'application/json'})
        self.assertEqual(res.status_code, 401)

    def test_updateConference(self):
        url = '/_ah/api/conference/v1/conference/dummy'
        res = urlfetch.fetch(self.urlbase + url,
                             payload=json.dumps({}),
                             method=urlfetch.PUT,
                             headers={'Content-Type': 'application/json'})
        self.assertEqual(res.status_code, 401)

    def test_getProfile(self):
        url = '/_ah/api/conference/v1/profile'
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 401)

    def test_getConferencesCreated(self):
        url = '/_ah/api/conference/v1/getConferencesCreated'
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 401)

    def test_getSessionsInWishlist(self):
        url = '/_ah/api/conference/v1/wishlist/dummy'
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 401)

    def test_getConferencesToAttend(self):
        url = '/_ah/api/conference/v1/conferences/attending'
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 401)

    def test_deleteSession(self):
        url = '/_ah/api/conference/v1/session/dummy'
        res = urlfetch.fetch(self.urlbase + url,
                             method=urlfetch.DELETE)
        self.assertEqual(res.status_code, 401)
