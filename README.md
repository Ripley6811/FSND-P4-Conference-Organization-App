#Conference Central App



##Links

[Conference Central Site](https://nice-tiger.appspot.com/#/)
[Deployed API Explorer](https://apis-explorer.appspot.com/apis-explorer/?base=https%3A%2F%2Fnice-tiger.appspot.com%2F_ah%2Fapi#p/conference/v1/)
[Localhost API Explorer](https://apis-explorer.appspot.com/apis-explorer/?base=http%3A%2F%2Flocalhost%3A8080%2F_ah%2Fapi#p/conference/v1/)


##Reference

[Cloud Endpoints](https://cloud.google.com/endpoints/)
[Protocal RPC field classes](https://cloud.google.com/appengine/docs/python/tools/protorpc/messages/fieldclasses)
[Using Datastore](https://cloud.google.com/appengine/docs/python/gettingstartedpython27/usingdatastore)
[How to avoid issuing RPCs in a loop](https://cloud.google.com/appengine/docs/python/ndb/entities)


##Process

- Stared for a long time at resources.
- Modeled the `createSession` method on the `updateConference` method because
it takes a conference key and a set of parameters. Created the SESS_POST_REQUEST
based on CONF_POST_REQUEST.


##Datastore notes

- `greeting = Greeting(parent=p_key)` : Creates an new instance
- `greeting.put()` : Saves the record to datastore
- `query = Greeting.query(ancestor=p_key).order(-Greeting.date)` : Query and order
- `query.fetch(10)` : Get 10 records
