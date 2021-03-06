#Conference Central App
> Steps required to successfully run the application.


####Using localhost server
To run a server on localhost open a terminal or cmd prompt in project root
directory and run `dev_appserver ConferenceCentral`. Then the application
web site can be found at http://localhost:8080 .

APIS-Explorer for local app is https://apis-explorer.appspot.com/apis-explorer/?base=http%3A%2F%2Flocalhost%3A8080%2F_ah%2Fapi#p/conference/v1/

**Warning:** On **Chrome**, you may get the following message:
*"You are exploring an API that is described or served via HTTP instead of HTTPS..."*
To resolve this, right-click on the shield at the end of the address bar and then click
"load unsafe scripts".

####Using deployment server
The deployed application URL is https://nice-tiger.appspot.com

APIS-Explorer for the deployed web site is https://apis-explorer.appspot.com/apis-explorer/?base=https%3A%2F%2Fnice-tiger.appspot.com%2F_ah%2Fapi#p/conference/v1/



###Sessions
> Sessions and speakers implementation including design decisions
behind the additional functionality.

*Related endpoints:*
- `createSession`
- `getConferenceSessions`
- `getConferenceSessionsByType`
- `getSessionsBySpeaker`

The `Session` model and related endpoints were implemented much like the
`Conference` model and endpoints. Session specific data fields were included, such as
having a reference to the parent Conference and a list of speakers.

The `createSession` method was modeled on the `updateConference` method because
it takes a conference key and a set of parameters. Created the SESS_POST_REQUEST
based on CONF_POST_REQUEST.

Speakers were implemented as a list in the `Session` model. Sessions sometimes
have multiple speakers and this was also a good way to learn how to use
list-related queries, particularly how to find one person within the lists of
multiple records.

*Session Fields*
- **name** is the name of the session and is type *string*
- **highlights** is a *string* description
- **speaker** is an *array of strings* to accomodate multiple speakers
- **typeOfSession** is a short *string* description of session
- **date** uses the *date* property type
- **startTime** uses the *time* property type
- **duration** is an *integer* representing session duration in minutes
- **conferenceKey** is a convenience reference to parent Conference as a websafe *string*

The session *name*, *date*, *startTime*, and *conferenceKey* are required.


###Wishlist
> How the wishlist works.

*Related endpoints:*
- `addSessionToWishlist`
- `getSessionsInWishlist`

Sessions are added to a profile as a list of session datastore keys.
The endpoint `getSessionsInWishlist` requires a conference key and processes the list of
session keys in the profile. A list of sessions is returned belonging to a
particular conference.


###Additional Queries (Endpoints)
> List additional endpoints and their implementation and design.

*Related endpoints:*
- `updateSession`
- `deleteSession`
- `getConferenceSessionsBySpeaker`

I added the (obvious) methods of *updating* and *deleting* sessions. These
were closely based on the conference endpoints. They check if the
user has authority to make changes by being the conference creator.

I also added an endpoint to return all sessions by a speaker in a particular
conference.


###Problematic Query
> How would you handle a query for all non-workshop sessions before 7 pm?
What is the problem with implementing this query?
What ways to solve it did you think of?

*Related endpoints:*
- `getTypeAndTime`

The special query problem points out the restriction that an inequality
filter can only be applied to one property within a single query.
"Non-workshop sessions" is one inequality filter related to *type*
and "sessions before 7pm"
is an inequality filter on a different property regarding *time*.
One way around this is to retrieve the results using one filter and then
proceed to programmatically filter the results by the other property.
The best way is to first filter for session *type*. Then take advantage of query
ordering of *type*, then *date* and *time*. Follow this with
a programmed filter to remove sessions starting at 7pm or later.

If filtering by *startTime* first, then
we cannot order by *date* before *startTime* because of another restriction where
the first ordering property must match the filtering property.

This is implemented in the `getTypeAndTime` endpoint
for demonstration. This endpoint can be expanded upon but is currently
hardcoded to demonstrate one solution to applying two inequalities of
different properties in a single request.


###Featured Speaker
> Implementation of the featured speaker endpoint.

*Related endpoints:*
- `getFeaturedSpeaker`

If a speaker for a new session is discovered to already have other conference
sessions, then that speaker's name is stored as a string in *memcache*.

This is detected during each call to the **conference.createSession**
endpoint. A task is added to the default *push queue* for each speaker in the
new session's speaker list. The task runs the **SetFeaturedSpeakerHandler** (main.py) which
updates the memcache key for a particular conference with a new speaker name (string)
if the speaker already has other sessions in the datastore.


###Running Tests
I spent a lot of time learning how to implement tests. The initial idea was to
have a test suite ensure
that everything works properly rather than testing each endpoint manually.
Numerous strange
problems had to be overcome. How to simulate a user for authenticated testing and
how to use and reset a **test datastore** for each test are just a couple that I
needed to resolve.

Logging in and out *during* tests proved too complicated so my solution was to
do all authenticated testing locally with a mock user account and unauthenticated
testing on the deployed app. In other words, localhost testing ensures
authenticated actions work correctly and deployed testing ensures
**non**-authenticated responses are correct.


####Localhost testing — `http://localhost:8080/tests`
Run the localhost server with `dev_appserver ConferenceCentral`.
Run localhost tests by going to the `http://localhost:8080/tests` url.

**Note:** Localhost tests may fail on the first run. Something to do with
the *stubs* not activating properly after an update. Refresh (hit F5) the
browser and all tests should pass on the following attempts.

Endpoint testing includes the `getTypeAndTime` endpoint and *wishlist* related
endpoints.

####Deployment testing — `https://nice-tiger.appspot.com/tests`
Deployed testing does not use a mock user account and tests that the endpoints
give the proper unauthorized response messages.
Run deployment tests by going to the https://nice-tiger.appspot.com/tests url.


##Links

- [Conference Central Site](https://nice-tiger.appspot.com/#/)
- [Deployed API Explorer](https://apis-explorer.appspot.com/apis-explorer/?base=https%3A%2F%2Fnice-tiger.appspot.com%2F_ah%2Fapi#p/conference/v1/)
- [Localhost API Explorer](https://apis-explorer.appspot.com/apis-explorer/?base=http%3A%2F%2Flocalhost%3A8080%2F_ah%2Fapi#p/conference/v1/)


##Reference

- [Cloud Endpoints](https://cloud.google.com/endpoints/)
- [Protocal RPC field classes](https://cloud.google.com/appengine/docs/python/tools/protorpc/messages/fieldclasses)
- [Using Datastore](https://cloud.google.com/appengine/docs/python/gettingstartedpython27/usingdatastore)
- [How to avoid issuing RPCs in a loop](https://cloud.google.com/appengine/docs/python/ndb/entities)
- [GAE Local testing](https://cloud.google.com/appengine/docs/python/tools/localunittesting)
- [How to integrate local testing as endpoint](https://www.altamiracorp.com/blog/employee-posts/unit-testing-google-app-engine)
- [`unittest` documentation](https://docs.python.org/2/library/unittest.html#unittest.TextTestRunner)
- [webapp2 Response class documentation](https://webapp-improved.appspot.com/api/webapp2.html#webapp2.Response)


##Datastore notes

- `greeting = Greeting(parent=p_key)`
    - Creates an new instance w/ parent
- `greeting.put()`
    - Saves the record to datastore
- `query = Greeting.query(ancestor=p_key).order(-Greeting.date)`
    - Query and reverse order
- `query.fetch(10)`
    - Get 10 records
- `query.get()`
    - Returns first record or `None`
