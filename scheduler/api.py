from flask import Flask, request, Response
from redis import Redis
from oauth2client import client
from apiclient import discovery
import googleapiclient
import functools
import flask
import json
import uuid
import httplib2

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())
redis = Redis(host='redis', port=6379)
root = "/api/1.0"
import json


### Health Checks

# PING
@app.route('/')
def ping():
    count = redis.incr('hits')
    return 'Hello World! I have been seen {} times.\n'.format(count)


### Events


# ALL
@app.route(root + "/events", methods=["GET", "POST", "DELETE"])
def events():
    if request.method == "GET":
        # return "List of all Events"
        all_events = json.dumps([eval(redis.get(key).decode('utf8')) for key in redis.scan_iter("event-*")])
        return Response(all_events, status=200)
    elif request.method == "POST":
        body = json.loads(request.get_data())
        for body_event in body["events"]:
            redis.set("event-" + body_event["id"], json.dumps(body_event))
        return Response("OK", status=200)
    elif request.method == "DELETE":
        redis.flushall()
        return Response("Events Deleted", status=200)
    else:
        return Response("Invalid Method", status=400)


# ONE
@app.route(root + "/events/<id>", methods=["GET", "POST"])
def event(id):
    if request.method == "GET":
        return redis.get("event-" + id)
    elif request.method == "POST":
        redis.set("event-" + id, request.get_data())
        return Response("OK", status=200)
    else:
        return Response("Invalid Method", status=400)


### Rotas

# ALL
@app.route(root + "/rotas", methods=["GET", "POST"])
def rotas():
    if request.method == "GET":
        # return "List of all Events"
        all_events = [eval(redis.get(key).decode('utf8')) for key in redis.scan_iter("event-*")]
        all_rotas = []
        for event in all_events:
            all_rotas.append({"rotas": event['rotas']})
        return Response(json.dumps(all_rotas), status=200)
    elif request.method == "POST":
        body = json.loads(request.get_data())
        for body_rota in body["rotas"]:
            redis.set("rota-" + body_rota["id"], body_rota)
        return Response("OK", status=200)
    else:
        return Response("Invalid Method", status=400)


# ONE
@app.route(root + "/rotas/<id>", methods=["GET", "POST"])
def rota(id):
    if request.method == "GET":
        return redis.get("rota-" + id)
    elif request.method == "POST":
        redis.set("rota-" + id, request.get_data())
        return Response("OK", status=200)
    else:
        return Response("Invalid Method", status=400)


### People

# ALL
@app.route(root + "/people", methods=["GET", "POST"])
def people():
    if request.method == "GET":
        return "Person: List"
    elif request.method == "POST":
        body = json.loads(request.get_data())
        for body_person in body["people"]:
            redis.set("person-" + body_person["id"], body_person)
        return Response("OK", status=200)
    else:
        return Response("Invalid Method", status=400)


# ONE
@app.route(root + "/people/<id>", methods=["GET", "POST"])
def person(id):
    if request.method == "GET":
        return redis.get("person-" + id)
    elif request.method == "POST":
        redis.set("person-" + id, request.get_data())
        return Response("OK", status=200)
    else:
        return Response("Invalid Method", status=400)


### Adapter: google

google_root = '/google/1.0'


def with_google_auth(handler):
    @functools.wraps(handler)
    def decorated_function(*args, **kwargs):
        if 'google_credentials' not in flask.session:
            flask.session['google_oauth2_redirect'] = request.full_path
            return flask.redirect(flask.url_for('google_oauth2'))

        credentials = client.OAuth2Credentials.from_json(
            flask.session['google_credentials'])
        if credentials.access_token_expired:
            flask.session['google_oauth2_redirect'] = request.full_path
            return flask.redirect(flask.url_for('google_oauth2'))

        http_auth = credentials.authorize(httplib2.Http())
        return handler(*args, http_auth=http_auth, **kwargs)
    return decorated_function


@app.route(google_root + '/oauth2')
def google_oauth2():
    flow = client.flow_from_clientsecrets(
        'client_secrets.json',
        scope=('https://www.googleapis.com/auth/spreadsheets.readonly'
               ' https://www.googleapis.com/auth/drive.metadata.readonly'
               ' https://www.googleapis.com/auth/calendar'),
        redirect_uri=flask.url_for('google_oauth2', _external=True))

    if 'code' not in request.args:
        # Step 1.
        return flask.redirect(flow.step1_get_authorize_url())

    else:
        # Step 2.
        auth_code = request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        flask.session['google_credentials'] = credentials.to_json()

        # Finished - go to the target URL
        return flask.redirect(flask.session['google_oauth2_redirect'])


### Adapter: google_sheet

@app.route(google_root + '/sheets')
@with_google_auth
def google_sheets(http_auth):
    service = discovery.build('drive', 'v3', http=http_auth)

    response = service.files().list(
        q='mimeType="application/vnd.google-apps.spreadsheet"',
        orderBy='modifiedTime desc',
    ).execute()

    return json.dumps([
        dict(name=x['name'], id=x['id'])
        for x in response['files']
    ])


@app.route(google_root + '/sheets/<id>/subsheets')
@with_google_auth
def google_sheets_subsheets(id, http_auth):
    service = discovery.build('sheets', 'v4', http=http_auth)

    response = service.spreadsheets().get(spreadsheetId=id).execute()

    return json.dumps([
        dict(name=p['title'], id=p['sheetId'])
        for p in (x['properties'] for x in response['sheets'])
        if p['sheetType'] == 'GRID'
    ])


@app.route(google_root + '/sheets/<id>/subsheets/<int:subsheet_id>/import',
           methods=['GET'])
@with_google_auth
def google_sheets_subsheets_import(id, subsheet_id, http_auth):
    service = discovery.build('sheets', 'v4', http=http_auth)

    response = service.spreadsheets().get(
        spreadsheetId=id,
        includeGridData=True
    ).execute()

    row_data = response['sheets'][subsheet_id]['data'][0]['rowData']

    values = [[cell.get('formattedValue') for cell in row['values']]
              for row in row_data]

    ###
    def prepare_for_service(values):
        body = json.dumps({
            "events": parse_values(values)
        })
        h = httplib2.Http('.cache')
        (resp, content) = h.request(
            'https://a472d6c9.ngrok.io/api/1.0/events',
            'POST',
            body=body
        )
        return content

    def parse_values(values):
        """
        Parses results from google sheets
        and creates a json object
        """
        events = []
        rota_names = []
        for index, row in enumerate(values):
            if index == 0:
                rota_names = row[2:]
            if index > 1:
                events.append({
                    "id": str(uuid.uuid4()),
                    "name": row[1],
                    "start": row[0],
                    "rotas": map_names_to_rotas(row[2:], rota_names)
                })
        return events

    def map_names_to_rotas(names, rota_names):
        rotas = []
        for index, name in enumerate(names):
            rotas.append({
                "name": rota_names[index],
                "people": list(map(lambda x: x.strip(), name.split(',')))
            })
        return rotas


    return prepare_for_service(values)


### Adapter: google_calendar

@app.route(google_root + '/calendars')
@with_google_auth
def google_calendars(http_auth):
    service = discovery.build('calendar', 'v3', http=http_auth)

    response = service.calendarList().list().execute()

    return json.dumps(
        [dict(id=x['id'], summary=x['summary'], description=x.get('description'))
         for x in response['items']]
    )

@app.route(google_root + '/calendar/<id>/upsert')
@with_google_auth
def google_calendar_upsert(id, http_auth):
    service = discovery.build('calendar', 'v3', http=http_auth)

    # TODO: temporary
    h = httplib2.Http('.cache')
    (resp, content) = h.request(
        'https://a472d6c9.ngrok.io/api/1.0/events', 'GET'
    )
    events = json.loads(content.decode('utf-8'))

    for event in events:
        event_id = event['id'].replace('-', '')

        # Get Event Ids in Calendar which match something
        try:
            service.events().get(calendarId=id, eventId=event_id).execute()
            event_found = True
        except googleapiclient.errors.HttpError as e:
            if e.resp['status'] != '404':
                raise e
            event_found = False

        description = '\n'.join(
            '%s: %s' % (rota['name'], ', '.join(rota['people']))
            for rota in event['rotas']
        )
        body = dict(
            id=event_id,
            summary=event['name'],
            start=dict(date=event['start']),
            end=dict(date=event['start']),
            description=description,
        )
        if event_found:
            service.events().update(calendarId=id, eventId=event_id, body=body).execute()
        else:
            service.events().insert(calendarId=id, body=body).execute()
    return Response("OK", status=200)

