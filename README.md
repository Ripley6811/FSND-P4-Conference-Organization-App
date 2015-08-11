#Conference Central App
> "Explain the steps required to successfully run the application."

I spent a lot of time learning how to do testing. One confusing problem after
another but I prevailed. I hope going above and beyond with testing makes up
for just meeting minimum requirements in other areas or the project.

###Localhost:8080
To run a server on localhost open CMD in project root directory and
run `dev_appserver ConferenceCentral`.

Chrome usage tip:
Warning: "You are exploring an API that is described or served via HTTP
instead of HTTPS..."
Right click on the shield at the end of the address bar and then click
"load unsafe scripts".


###Sessions
> "Explain how sessions and speakers are implemented including design decisions
behind the additional functionality."

*Related endpoints:*
- `createSession`
- `getConferenceSessions`
- `getConferenceSessionsByType`
- `getSessionsBySpeaker`

The `Session` model and related endpoints were implemented much like the
`Conference` model and endpoints. With some session specific data, such as
having a reference to the parent Conference and a list of speakers.

Speakers were implemented as a list in the `Session` model. Sessions sometimes
have multiple speakers and this was also a good way to learn how to use
list-related queries, particularly how to find one person within the lists of
multiple records.


###Wishlist
> "Explain how the wishlist works."

*Related endpoints:*
- `addSessionToWishlist`
- `getSessionsInWishlist`

Sessions are added to a profile as a list of session datastore keys.
The endpoint `getSessionsInWishlist` requires a conference key and processes the list of
session keys in the profile. A list of sessions is returned belong to a
particular conference.


###Additional Queries (Endpoints)
> "List the additional endpoints and explain their implementation and design."

*Related endpoints:*
- `getConferenceSessionsBySpeaker`
- `updateSession`
- `deleteSession`

I added the (obvious) methods of *updating* and *deleting* sessions. These
were closely based on the conference endpoints but also check whether the
user has authority to make changes by being the conference creator.

I also added an endpoint to return all sessions by a speaker in a particular
conference.


###Problematic Query
> "Explain the query problem and describe the solution."

*Related endpoints:*
- `getTypeAndTime`

The special query problem points out the restriction that an inequality
filter can only be applied to one property.
"Non-workshop sessions" is one inequality filter related to *type*
and "sessions before 7pm"
is an inequality filter on a different property regarding *time*.
One way around this is to retrieve the results using one filter and then
proceed to programmatically filter the results by the other property.
The best way is to filter for session type, then take advantage of query
ordering of type, date and time. Followed by
a programmatic filter to remove sessions starting at 7pm or later.

This is implemented in the `getTypeAndTime` endpoint
for demonstration. This endpoint can be expanded upon but is currently
hardcoded to demonstrate one solution to applying multiple inequalities of
different properties in a query.


###Featured Speaker
> "Explain how the featured speaker was implemented."

*Related endpoints:*
- `getFeaturedSpeaker`

If a speaker for a new session is discovered to already have other conference
sessions, then that speaker's name is stored as a string in *memcache*.
This is detected and updated during each call to the **conference.createSession**
endpoint.


###Running Tests
####Localhost testing — `http://localhost:8080/tests`
Run the localhost server with `dev_appserver ConferenceCentral`.
Localhost testing uses a mock user account and tests endpoints using that user.
Run localhost tests by going to the `http://localhost:8080/tests` url.

**Note:** Localhost tests may fail on the first run. Something to do with
the *stubs* not activating properly after an update. Refresh (hit F5) the
browser and all tests should pass on the following attempts.
####Deployment testing — `https://nice-tiger.appspot.com/tests`
Deployed testing does not use a mock user account and tests that the endpoints
give the proper unauthorized response messages.
Run deployment tests by going to the `https://nice-tiger.appspot.com/tests` url.


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


##Process

- Stared for a long time at resources.
- Modeled the `createSession` method on the `updateConference` method because
it takes a conference key and a set of parameters. Created the SESS_POST_REQUEST
based on CONF_POST_REQUEST.


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
