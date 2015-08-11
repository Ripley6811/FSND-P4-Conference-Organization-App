#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'


from os import environ
from datetime import datetime, time
from functools import wraps

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import StringMessage
from models import BooleanMessage
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import Session
from models import SessionForm
from models import SessionForms
#from models import SessionQueryForm  # Not yet implemented
#from models import SessionQueryForms  # Not yet implemented
from models import TeeShirtSize

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
ANNOUNCEMENT_TPL = ('Last chance to attend! The following conferences '
                    'are nearly sold out: %s')
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": [ "Default", "Topic" ],
}

OPERATORS = {
            'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
            }

FIELDS =    {
            'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
            }

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_GET_REQUEST_BY_TYPE = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
    typeOfSession=messages.StringField(2),
)

CONF_GET_REQUEST_BY_SPEAKER = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
    speaker=messages.StringField(2),
)

SPEAKER_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speaker=messages.StringField(1),
)

CONF_PUT_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

SESS_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSessionKey=messages.StringField(1),
)

SESS_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESS_PUT_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeSessionKey=messages.StringField(1),
)


# - - - Decorators - - - - - - - - - - - - - - - - - - - - - -

TEST_APP = True
TEST_WITH_MOCK_AUTH = True  # Mock authorization always on
def checks_authorization(func):
    """Decorator for first checking user login state before proceeding
    with function. Raises 401 unauthorized error if not logged in. Passes
    `user_id` as kwarg to the wrapped function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # If testing app, ensure it is running on dev_appserver localhost
        if TEST_APP and environ['SERVER_SOFTWARE'].startswith('Dev'):
            if TEST_WITH_MOCK_AUTH:
                # Always authorized
                user = users.User(email='authorize@all.com')
            else:
                # Use current user if it exists
                user = users.get_current_user()
            if not user:
                raise endpoints.UnauthorizedException('Authorization required')
        else:
            # Endpoints login check
            user = endpoints.get_current_user()
            if not user:
                raise endpoints.UnauthorizedException('Authorization required')

        return func(*args, user=user, **kwargs)
    return wrapper

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(name='conference', version='v1',
               audiences=[ANDROID_AUDIENCE],
               allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID,
                                   ANDROID_CLIENT_ID, IOS_CLIENT_ID],
               scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf


    @checks_authorization
    def _createConferenceObject(self, request, user=None):
        """Create Conference object, returning ConferenceForm/request."""
        user_id = getUserId(user)
        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': p_key.get().mainEmail,
            'conferenceInfo': repr(request)},
            url='/tasks/send_confirmation_email'
        )
        return request


    @checks_authorization
    @ndb.transactional
    def _updateConferenceObject(self, request, user=None):
        # copy ConferenceForm/ProtoRPC Message into dict
        user_id = getUserId(user)
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))


    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
            http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)


    @endpoints.method(CONF_PUT_REQUEST, ConferenceForm,
            path='conference/{websafeConferenceKey}',
            http_method='PUT', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)


    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
            path='conference/{websafeConferenceKey}',
            http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))


    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='getConferencesCreated',
            # 2015 Jul 4, JWJ, Changed from POST to GET
            http_method='GET', name='getConferencesCreated')
    @checks_authorization
    def getConferencesCreated(self, request, user=None):
        """Return conferences created by user."""
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, getattr(prof, 'displayName'))
                   for conf in confs]
        )


    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q


    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name) for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)


    @endpoints.method(ConferenceQueryForms, ConferenceForms,
            path='queryConferences',
            http_method='POST',
            name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId)) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
                items=[self._copyConferenceToForm(conf, names[conf.organizerUserId]) for conf in \
                conferences]
        )


# - - - Session objects - - - - - - - - - - - - - - - - - - -

    def _copySessionToForm(self, sess):
        """Copy relevant fields from Session to SessionForm."""
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(sess, field.name):
                # convert Date and Time to string; just copy others
                if field.name in ['date', 'startTime']:
                    setattr(sf, field.name, str(getattr(sess, field.name)))
                else:
                    setattr(sf, field.name, getattr(sess, field.name))
            elif field.name == 'websafeKey':
                # Add datastore key for reference
                setattr(sf, field.name, sess.key.urlsafe())
        sf.check_initialized()
        return sf


    @checks_authorization
    def _createSessionObject(self, request, user=None):
        """Create Session object, returning SessionForm/request."""
        user_id = getUserId(user)
        # get Conference object from request; bail if not found
        wck = request.websafeConferenceKey
        c_key = ndb.Key(urlsafe=wck)
        conf = c_key.get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wck)

        # Check editing authorization. Creater and user match
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only conference creator may add sessions')

        if not request.name or not request.date or not request.startTime:
            raise endpoints.BadRequestException(
                "Session 'name', 'date', and 'startTime' fields required")

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        data['conferenceKey'] = wck
        data.pop('websafeConferenceKey', None)
        data.pop('websafeKey', None)

        # convert date/time strings to Date/Time objects
        if data['date']:
            data['date'] = datetime.strptime(
                                data['date'][:10], "%Y-%m-%d").date()
        if data['startTime']:
            data['startTime'] = datetime.strptime(
                                    data['startTime'][:10], "%H:%M").time()

        # Check date is within conference date range (if specified)
        if conf.startDate and conf.endDate:
            if data['date'] < conf.startDate or data['date'] > conf.endDate:
                raise endpoints.BadRequestException(
                    "Session date is not within conference timeframe.")

        # generate Session Key based on parent key
        s_id = Session.allocate_ids(size=1, parent=c_key)[0]
        s_key = ndb.Key(Session, s_id, parent=c_key)
        data['key'] = s_key

        # create Session & return (modified) SessionForm
        sess = Session(**data)
        sess.put()

        # Set new featured speaker in memcache if necessary
        for speaker in data['speaker']:
            sessions = self._conferenceSessionsBySpeaker(wck, speaker)
            if sessions.count() >= 2:
                memcache.set(key="featuredSpeaker_" + wck, value=speaker)

        return self._copySessionToForm(sess)


    @checks_authorization
    @ndb.transactional
    def _updateSessionObject(self, request, user=None):
        """Update Session object, returning SessionForm/request."""
        user_id = getUserId(user)
        wsk = request.websafeSessionKey

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # update existing session
        s_key = ndb.Key(urlsafe=wsk)
        sess = s_key.get()
        # check that session exists
        if not sess:
            raise endpoints.NotFoundException(
                'No session found with key: %s' % wsk)

        # check that user is owner
        if user_id != s_key.parent().get().organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the session.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from SessionForm to Session object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name == 'date':
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                elif field.name == 'startTime':
                    data = datetime.strptime(data, "%H:%M").time()
                # write to Session object
                setattr(sess, field.name, data)

        # Commit changes and return SessionForm
        sess.put()
        return self._copySessionToForm(sess)


    @checks_authorization
    @ndb.transactional
    def _deleteSessionObject(self, request, user=None):
        """Delete Session object, returning boolean."""
        user_id = getUserId(user)
        # get Session object from request; bail if not found
        wsk = request.websafeSessionKey
        s_key = ndb.Key(urlsafe=wsk)
        if not s_key.get():
            raise endpoints.NotFoundException(
                'No session found with key: %s' % wsk)

        # Delete entity and return boolean
        s_key.delete()
        return BooleanMessage(data=True)


    @endpoints.method(CONF_GET_REQUEST, SessionForms,
                      path='conference/{websafeConferenceKey}/session',
                      http_method='GET', name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Given a conference, return all sessions in chronological order."""
        wck = request.websafeConferenceKey
        # get Conference object from request; bail if not found
        c_key = ndb.Key(urlsafe=wck)
        if not c_key.get():
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wck)

        # Get sessions for conference ordered by time and return list
        s_query = Session.query(ancestor=c_key)
        s_query = s_query.order(Session.date)
        s_query = s_query.order(Session.startTime)
        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in s_query]
        )


    @endpoints.method(CONF_GET_REQUEST_BY_TYPE, SessionForms,
          path='conference/{websafeConferenceKey}/sessiontype/{typeOfSession}',
          http_method='GET', name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Given a conference, return all sessions of a specified type (eg
        lecture, keynote, workshop)."""
        wck = request.websafeConferenceKey
        # get Conference object from request; bail if not found
        c_key = ndb.Key(urlsafe=wck)
        if not c_key.get():
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wck)

        # Get sessions for conference and particular type and return list
        s_query = Session.query(ancestor=c_key)
        s_query = s_query.filter(Session.typeOfSession==request.typeOfSession)
        s_query = s_query.order(Session.date)
        s_query = s_query.order(Session.startTime)
        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in s_query]
        )


    @endpoints.method(SPEAKER_GET_REQUEST, SessionForms,
              path='speaker/{speaker}',
              http_method='GET', name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Given a speaker, return all sessions given by this particular
        speaker, across all conferences."""
        # Get sessions for particular speaker and return list
        s_query = Session.query()
        s_query = s_query.filter(Session.speaker == request.speaker)
        s_query = s_query.order(Session.date)
        s_query = s_query.order(Session.startTime)
        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in s_query]
        )


    def _conferenceSessionsBySpeaker(self, wck, speaker):
        # get Conference object from request; bail if not found
        c_key = ndb.Key(urlsafe=wck)
        if not c_key.get():
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wck)

        # Get sessions for conference and particular speaker and return list
        s_query = Session.query(ancestor=c_key)
        # NOTE: Should this be "IN"
        s_query = s_query.filter(Session.speaker == speaker)
        s_query = s_query.order(Session.date)
        s_query = s_query.order(Session.startTime)
        return s_query



    @endpoints.method(CONF_GET_REQUEST_BY_SPEAKER, SessionForms,
              path='conference/{websafeConferenceKey}/speaker/{speaker}',
              http_method='GET', name='getConferenceSessionsBySpeaker')
    def getConferenceSessionsBySpeaker(self, request):
        """Given a conference and speaker, return all sessions given by this
        particular speaker at this particular conference."""
        sessions = self._conferenceSessionsBySpeaker(
                            request.websafeConferenceKey,
                            request.speaker
        )
        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in sessions]
        )


    @endpoints.method(SESS_POST_REQUEST, SessionForm,
                      path='conference/{websafeConferenceKey}/session',
                      http_method='POST', name='createSession')
    def createSession(self, request):
        """Create a session. Open only to the organizer of the conference."""
        return self._createSessionObject(request)


    @endpoints.method(SESS_PUT_REQUEST, SessionForm,
                      path='session/{websafeSessionKey}',
                      http_method='PUT', name='updateSession')
    def updateSession(self, request):
        """Update session with provided fields & return with updated info."""
        return self._updateSessionObject(request)


    @endpoints.method(SESS_GET_REQUEST, BooleanMessage,
                      path='session/{websafeSessionKey}',
                      http_method='DELETE', name='deleteSession')
    def deleteSession(self, request):
        """Delete a session. Open only to the organizer of the conference."""
        return self._deleteSessionObject(request)


    @endpoints.method(SESS_GET_REQUEST, BooleanMessage,
                      path='wishlist/{websafeSessionKey}',
                      http_method='POST', name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        """Add session to user's wishlist."""
        wsk = request.websafeSessionKey
        # get user Profile
        prof = self._getProfileFromUser()
        # check if session exists
        s_key = ndb.Key(urlsafe=wsk)
        if not s_key.get():
            raise endpoints.NotFoundException(
                'No session found with key: %s' % wsk)

        # check if user already registered otherwise add
        if wsk in prof.sessionKeysToAttend:
            raise ConflictException(
                "You have already added this session to your wishlist")

        # register user, take away one seat
        prof.sessionKeysToAttend.append(wsk)

        # write things back to the datastore & return
        prof.put()
        return BooleanMessage(data=True)


    @endpoints.method(CONF_GET_REQUEST, SessionForms,
                      path='wishlist/{websafeConferenceKey}',
                      http_method='GET', name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Get a list of all sessions in user's wishlist for a particular
        conference."""
        # get user Profile
        prof = self._getProfileFromUser()
        wck = request.websafeConferenceKey
        # get Conference object from request; bail if not found
        c_key = ndb.Key(urlsafe=wck)
        if not c_key.get():
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wck)

        # Convert session IDs to ndb Keys
        s_keys = [ndb.Key(urlsafe=s_id) for s_id in prof.sessionKeysToAttend]

        # Filter the keys with the correct conference parent key
        s_keys = [k for k in s_keys if k.parent() == c_key]

        # Load entities, skipping deleted sessions (NoneType)
        sessions = [s for s in ndb.get_multi(s_keys) if s]

        # Order the sessions by date and time
        sessions = sorted(sessions, key=lambda s: (s.date, s.startTime))

        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in sessions]
        )


    @endpoints.method(CONF_GET_REQUEST, StringMessage,
                      path='conference/featuredspeaker',
                      http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Get the name of the currently featured speaker for a conference"""
        wck = request.websafeConferenceKey
        # get Conference object from request; bail if not found
        c_key = ndb.Key(urlsafe=wck)
        if not c_key.get():
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wck)
        return StringMessage(data=memcache.get('featuredSpeaker_' + wck) or "")


    @endpoints.method(CONF_GET_REQUEST, SessionForms,
                      path='conference/{websafeConferenceKey}/typeandtime',
                      http_method='GET', name='getTypeAndTime')
    def getTypeAndTime(self, request):
        """Get the result for a special query.

        This method tests the solution to the non-workshop & before 7pm query
        problem."""
        wck = request.websafeConferenceKey
        # get Conference object from request; bail if not found
        c_key = ndb.Key(urlsafe=wck)
        if not c_key.get():
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wck)


        # Get sessions for conference and particular speaker and return list
        s_query = Session.query(ancestor=c_key)
        # NOTE: Should this be "IN"
        s_query = s_query.filter(Session.typeOfSession != 'workshop')
        s_query = s_query.order(Session.typeOfSession)
        s_query = s_query.order(Session.date)
        s_query = s_query.order(Session.startTime)

        records = [sess for sess in s_query if sess.startTime < time(19)]

        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in records]
        )


# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf


    @checks_authorization
    def _getProfileFromUser(self, user=None):
        """Return user Profile from datastore, creating new one if non-existent."""
        user_id = getUserId(user)
        # get Profile from datastore
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key = p_key,
                displayName = user.nickname(),
                mainEmail= user.email(),
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile


    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        #if field == 'teeShirtSize':
                        #    setattr(prof, field, str(val).upper())
                        #else:
                        #    setattr(prof, field, val)
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)


    @endpoints.method(message_types.VoidMessage, ProfileForm,
            path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()


    @endpoints.method(ProfileMiniForm, ProfileForm,
            path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement


    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='conference/announcement/get',
            http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        return StringMessage(data=memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY) or "")


# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser() # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)


    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='conferences/attending',
            http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser() # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck) for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copyConferenceToForm(conf, names[conf.organizerUserId])\
         for conf in conferences]
        )


    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)


    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)


    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='filterPlayground',
            http_method='GET', name='filterPlayground')
    def filterPlayground(self, request):
        """Filter Playground"""
        q = Conference.query()
        # field = "city"
        # operator = "="
        # value = "London"
        # f = ndb.query.FilterNode(field, operator, value)
        # q = q.filter(f)
        q = q.filter(Conference.city == "London")
        q = q.filter(Conference.topics == "Medical Innovations")
#        q = q.filter(Conference.month == 6)
#        q = q.order(Conference.name)
        q = q.filter(Conference.maxAttendees > 10)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )


api = endpoints.api_server([ConferenceApi]) # register API
