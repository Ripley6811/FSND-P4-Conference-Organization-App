#Conference Central App

###Localhost:8080
To run a server on localhost open CMD in project root directory and run `dev_appserver ConferenceCentral`.

Query problem points out the restriction that an inequality filter can only be applied to one property.
Non-workshop sessions is one inequality filter and sessions before 7pm is an inequality filter on a different property.
One way around this is to retrieve the results from one filter and then proceed to programmatically filter the results by the other property.
The best way is to filter for session type, then take advantage of query ordering of type, date and time. Followed by
a programmatic filter to remove sessions starting at 7pm or later. This is implemented in the `getTypeAndTime` endpoint
for demonstration. This endpoint can be expanded upon but is currently hardcoded to demonstrate solving a multiple inequalities of different properties problem.

Chrome usage tip:
Warning: "You are exploring an API that is described or served via HTTP instead of HTTPS..."
Right click on the shield at the end of the address bar and then click "load unsafe scripts".

###Sessions
"Explain how sessions and speakers are implemented including design decisions behind additional functionality."

###Wishlist
"Explain how the wishlist works."

###Additional Queries (Endpoints)
"List the additional endpoints and explain their implementation and design."

###Problematic Query
"Explain the query problem and describe the solution."

###Featured Speaker
"Explain how the featured speaker was implemented."

###Running Tests
#####Localhost testing — `http://localhost:8080/tests`
Run the localhost server with `dev_appserver ConferenceCentral`.
Localhost testing uses a mock user account and tests endpoints using that user.
Run localhost tests by going to the `http://localhost:8080/tests` url.
Note: Localhost tests usually fail on the first run. Something to do with the *stubs* not activating properly after an update. Refresh (hit F5) the browser and all tests should pass on the following attempts.
#####Deployment testing — `https://nice-tiger.appspot.com/tests`
Deployed testing does not use a mock user account and tests that the endpoints give the proper unauthorized response messages.
Run deployment tests by going to the `https://nice-tiger.appspot.com/tests` url.
The first load of `tests` page often fails with a server error or timeout. Reload the page (F5) and all tests should pass.


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
