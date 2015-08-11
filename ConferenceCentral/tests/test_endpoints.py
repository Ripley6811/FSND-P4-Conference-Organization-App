import unittest
import json
from time import sleep

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.ext import testbed
from google.appengine.api.app_identity import get_default_version_hostname

from models import Conference, Session, Profile
from datetime import date, time


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
        self.testbed.init_app_identity_stub()  # Routes to test datastore
        self.testbed.init_datastore_v3_stub()  # Creates test datastore
#        self.testbed.init_urlfetch_stub()  # !!RECURSION DEPTH EXCEEDED
        self.testbed.init_memcache_stub()
        ndb.get_context().clear_cache()
#        ndb.get_context().set_cache_policy(False)
        self.urlbase = 'http://{0}/_ah/api/conference/v1'.format(
                                get_default_version_hostname())

    def tearDown(self):
        ndb.get_context().clear_cache()
        self.testbed.deactivate()

    #### TESTS ####
    def test_getProfile(self):
        url = '/profile'
        res = urlfetch.fetch(self.urlbase + url, method='GET')
        self.assertEqual(res.status_code, 200)
        self.assertIn('@', json.loads(res.content)['mainEmail'])

    def test_createConference_BadRequest(self):
        url = '/conference'
        params = {}
        response = urlfetch.fetch(self.urlbase + url,
                        payload=json.dumps(params),
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 400)

    def test_createConference(self):
        # Ensure default profile is created
        url = '/profile'
        res = urlfetch.fetch(self.urlbase + url, method='GET')
        self.assertEqual(res.status_code, 200)
        # Test endpoint by adding a conference
        url = '/conference'
        params = {'name':'TEST Conference'}
        self.assertEqual(0, len(Conference.query().fetch(5)))
        response = urlfetch.fetch(self.urlbase + url,
                        payload=json.dumps(params),
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        sleep(0.1)
        # Check only one conference in database
        self.assertEqual(1, len(Conference.query().fetch(5)))
        # Check that the name matches the one submitted
        self.assertEqual(Conference.query().get().name, params['name'])

    def test_getConferencesCreated(self):
        url = '/getConferencesCreated'
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 200)
        sleep(0.1)
        self.assertEqual(len(Conference.query().fetch(5)), 0)

    def test_getConferenceSessions(self):
        # Create conference and get websafe key
        url = '/conference'
        conf = Conference(name='Test Conference')
        wck = conf.put()
        wcksafe = wck.urlsafe()
        # Add 4 sessions
        props = {'name': 'Monkey Business', 'date': date(2015,8,8),
                 'parent': wck, 'conferenceKey': wcksafe}
        Session(typeOfSession='workshop', startTime=time(10,15), **props).put()
        Session(typeOfSession='meetup', startTime=time(15,15), **props).put()
        Session(typeOfSession='social', startTime=time(19,15), **props).put()
        # Verify total conferences
        url = '/conference/{0}/session'.format(wcksafe)
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(json.loads(res.content)['items']), 3)

    def test_getConferenceSessionsByType(self):
        # Create conference and get websafe key
        conf = Conference(name='Test Conference')
        wck = conf.put()
        wcksafe = wck.urlsafe()
        # Add 4 sessions with speakers
        props = {'name': 'Monkey Business', 'date': date(2015,8,8),
                 'parent': wck, 'conferenceKey': wcksafe,
                 'startTime': time(18,15)}
        Session(typeOfSession='lecture', **props).put()
        Session(typeOfSession='workshop', **props).put()
        Session(typeOfSession='gathering', **props).put()
        Session(typeOfSession='lecture', **props).put()
        # Test the endpoint
        url = '/conference/{0}/sessiontype/{1}'.format(
                                                 wcksafe, 'lecture'
        )
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(json.loads(res.content)['items']), 2)

    def test_getSessionsBySpeaker(self):
        # Create two conferences
        conf = Conference(name='Test Conference A')
        wckA = conf.put()
        wckAsafe = wckA.urlsafe()
        conf = Conference(name='Test Conference B')
        wckB = conf.put()
        wckBsafe = wckB.urlsafe()
        # Add 4 sessions among conferences with three having particular speaker
        propsA = {'name': 'Monkey Business', 'date': date(2015,8,8),
                  'parent': wckA, 'conferenceKey': wckAsafe,
                  'typeOfSession': 'lecture', 'startTime': time(18,15)}
        propsB = {'name': 'Monkey Business', 'date': date(2015,9,12),
                  'parent': wckB, 'conferenceKey': wckBsafe,
                  'typeOfSession': 'workshop', 'startTime': time(12,15)}
        # Add two to first created conference
        Session(speaker=['Sarah', 'Frodo'], **propsA).put()
        Session(speaker=['Frodo'], **propsA).put()
        # Add two to second created conference
        Session(speaker=['Saruman'], **propsB).put()
        Session(speaker=['Gollum', 'Frodo'], **propsB).put()
        # Test the endpoint
        url = '/speaker/{0}'.format('Frodo')
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(json.loads(res.content)['items']), 3)

    def test_addSessionToWishlist(self):
        # Check that no profiles exist in datastore
        prof = Profile.query().get()
        self.assertEqual(prof, None)
        # Create conference and get websafe key
        conf = Conference(name='Test_conference')
        wck = conf.put()
        # Add a session
        props = {'name': 'Monkey Business', 'date': date(2015,8,8),
                 'parent': wck, 'conferenceKey': wck.urlsafe(),
                 'typeOfSession': 'lecture', 'startTime': time(18,15)}
        sk = Session(speaker=['Sarah', 'Frodo'], **props).put()
        # Test the endpoint (This also creates a Profile record)
        url = '/wishlist/{0}'.format(sk.urlsafe())
        res = urlfetch.fetch(self.urlbase + url, method='POST')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.content)['data'])
        sleep(0.1)
        # Get profile and check for one session key
        prof = Profile.query().get()
        self.assertEqual(len(prof.sessionKeysToAttend), 1)

    def test_getSessionsInWishlist(self):
        # Create conference and get websafe key
        conf = Conference(name='Test_conference')
        wck = conf.put()
        # Add a session
        props = {'name': 'Monkey Business', 'date': date(2015,8,8),
                 'parent': wck, 'conferenceKey': wck.urlsafe(),
                 'typeOfSession': 'lecture', 'startTime': time(18,15)}
        sk = Session(speaker=['Sarah', 'Frodo'], **props).put()
        # Have endpoint create default Profile record
        res = urlfetch.fetch(self.urlbase + '/profile')
        self.assertEqual(res.status_code, 200)
        sleep(0.1)
        # Create profile with session key in wishlist
        profile = Profile.query().get()
        profile.sessionKeysToAttend = [sk.urlsafe()]
        profile.put()
        # Test the endpoint
        url = '/wishlist/{0}'.format(wck.urlsafe())
        res = urlfetch.fetch(self.urlbase + url, method='GET')
        self.assertEqual(res.status_code, 200)
        # Test if one entry in returned items list
        self.assertEqual(len(json.loads(res.content)['items']), 1)

    # Test for the solution to the special query related problem.
    def test_getQuerySolution(self):
        # Create conference and get websafe key
        url = '/conference'
        conf = Conference(name='Test Conference')
        wck = conf.put()
        wcksafe = wck.urlsafe()
        # Add 4 sessions with 2 that will pass filter
        props = {'name': 'Monkey Business', 'date': date(2015,8,8),
                 'parent': wck, 'conferenceKey': wcksafe}
        Session(typeOfSession='workshop', startTime=time(10,15), **props).put()
        Session(typeOfSession='meetup', startTime=time(15,15), **props).put()
        Session(typeOfSession='flash', startTime=time(18,15), **props).put()
        Session(typeOfSession='social', startTime=time(19,15), **props).put()
        # Test the special query
        url = '/conference/{0}/typeandtime'.format(wcksafe)
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(json.loads(res.content)['items']), 2)

    def test_getConferenceSessionsBySpeaker(self):
        # Create conference and get websafe key
        conf = Conference(name='Test Conference')
        wck = conf.put()
        wcksafe = wck.urlsafe()
        # Add 4 sessions with speakers
        props = {'name': 'Monkey Business', 'date': date(2015,8,8),
                 'parent': wck, 'conferenceKey': wcksafe,
                 'typeOfSession': 'lecture', 'startTime': time(18,15)}
        Session(speaker=['Sarah Baggins', 'Frodo Baggins'], **props).put()
        Session(speaker=['Frodo Baggins'], **props).put()
        Session(speaker=['Saruman'], **props).put()
        Session(speaker=['Gollum', 'Legolas'], **props).put()
        # Test the endpoint
        url = '/conference/{0}/speaker/{1}'.format(
                            wcksafe, 'Frodo%20Baggins'
        )
        res = urlfetch.fetch(self.urlbase + url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(json.loads(res.content)['items']), 2)

    def test_createSession(self):
        test_url = '/conference/{wcksafe}/session'
        # Ensure default profile is created
        url = '/profile'
        res = urlfetch.fetch(self.urlbase + url, method='GET')
        self.assertEqual(res.status_code, 200)
        # Create conference and get websafe key
        conf = Conference(
            name='Test Conference',
            organizerUserId=json.loads(res.content)['mainEmail']
        )
        wck = conf.put()
        sleep(0.1)
        wcksafe = wck.urlsafe()
        test_url = test_url.format(wcksafe=wcksafe)
        # Ensure no sessions exist yet
        self.assertEqual(0, len(Session.query().fetch(5)))
        # Test endpoint
        params = {
            'name': 'TEST Session',
            'date': '2015-8-10',
            'startTime': '9:10',
            'conferenceKey': wcksafe
        }
        response = urlfetch.fetch(self.urlbase + test_url,
                        payload=json.dumps(params),
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)



    def test_getFeaturedSpeaker(self):
        test_url = '/conference/featuredspeaker?websafeConferenceKey={wcksafe}'
        sess_url = '/conference/{wcksafe}/session'
        # Ensure default profile is created
        url = '/profile'
        res = urlfetch.fetch(self.urlbase + url, method='GET')
        self.assertEqual(res.status_code, 200)
        # Create conference and get websafe key
        conf = Conference(
            name='Test Conference',
            organizerUserId=json.loads(res.content)['mainEmail']
        )
        wck = conf.put()
        wcksafe = wck.urlsafe()
        test_url = test_url.format(wcksafe=wcksafe)
        sess_url = sess_url.format(wcksafe=wcksafe)
        # Add a session with speaker
        props = {'name': 'Monkey Business', 'date': '2015-8-8',
                 'conferenceKey': wcksafe,
                 'typeOfSession': 'lecture', 'startTime': '18:00',
                 'speaker': ['Sarah Baggins', 'Frodo Baggins']}
        response = urlfetch.fetch(self.urlbase + sess_url,
                        payload=json.dumps(props),
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        # Test endpoint
        res = urlfetch.fetch(self.urlbase + test_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.content)['data'], '')
        # Add a second session with the previous speaker
        props = {'name': 'Bull Business', 'date': '2015-8-8',
                 'conferenceKey': wcksafe,
                 'typeOfSession': 'lecture', 'startTime': '11:15',
                 'speaker': ['Frodo Baggins']}
        response = urlfetch.fetch(self.urlbase + sess_url,
                        payload=json.dumps(props),
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        # Test endpoint again
        res = urlfetch.fetch(self.urlbase + test_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.content)['data'], 'Frodo Baggins')

