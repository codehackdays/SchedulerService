from flask import Flask, request, Response
from redis import Redis
from oauth2client import client
from apiclient import discovery
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
@app.route(root + "/events", methods=["GET", "POST"])
def events():
    if request.method == "GET":
        return "Event: List"
    elif request.method == "POST":
        body = json.loads(request.get_data())
        for body_event in body["events"]:
            redis.set("event-" + body_event["id"], body_event)
        return Response("OK", status=200)
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
        return "Rota: List"
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


### Adapter: google_sheet

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
               ' https://www.googleapis.com/auth/drive.metadata.readonly'),
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

    # Import code here!

    return json.dumps(values)
