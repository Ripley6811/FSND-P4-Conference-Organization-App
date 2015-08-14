#!/usr/bin/env python

"""
main.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access

$Id$

created by wesc on 2014 may 24
modified by JWJ on 2015 Jul 3

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

from os import environ
import webapp2
import unittest
from google.appengine.api import app_identity
from google.appengine.api import mail
from google.appengine.api import memcache
from conference import ConferenceApi


class SetAnnouncementHandler(webapp2.RequestHandler):
    def get(self):
        """Set Announcement in Memcache."""
        ConferenceApi._cacheAnnouncement()
        self.response.set_status(204)


class SendConfirmationEmailHandler(webapp2.RequestHandler):
    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created a following '         # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )


class SetFeaturedSpeakerHandler(webapp2.RequestHandler):
    def post(self):
        wck = self.request.get('websafeConferenceKey')
        speaker = self.request.get('speaker')
        # Set new featured speaker in memcache if necessary
        sessions = ConferenceApi._conferenceSessionsBySpeaker(wck, speaker)
        if sessions.count() >= 2:
            memcache.set(key="featuredSpeaker_" + wck, value=speaker)


class TestSuiteHandler(webapp2.RequestHandler):
    def get(self):
        # Test if running on dev_appserver or cloud server
        localtest = environ['SERVER_SOFTWARE'].startswith('Dev')
        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        self.response.headers['Content-Type'] = 'text/plain'
        if localtest:
            # Run datastore and authorized endpoint tests
            self.response.write("=================\n")
            self.response.write(" Localhost Tests \n")
            self.response.write("=================\n\n")
            suite.addTest(loader.discover('tests', 'test_datastore.py'))
            suite.addTest(loader.discover('tests', 'test_endpoints.py'))
        else:
            # Run datastore and UNauthorized enpoint tests
            self.response.write("==================\n")
            self.response.write(" Deployment Tests \n")
            self.response.write("==================\n\n")
            suite.addTest(loader.discover('tests', 'test_datastore.py'))
            suite.addTest(loader.discover('tests', 'test_unauth*.py'))
        # TextTestRunner requires flush-able stream. Add empty function.
        self.response.flush = lambda: None
        unittest.TextTestRunner(self.response).run(suite)


app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ('/tasks/set_featured_speaker', SetFeaturedSpeakerHandler),
    ('/tests', TestSuiteHandler),
], debug=True)
