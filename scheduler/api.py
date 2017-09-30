from flask import Flask, request
from redis import Redis

app = Flask(__name__)
redis = Redis(host='redis', port=6379)

root = "/api/1.0"


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
        return "Event: List"
    else:
        return {}, 400


# ONE
@app.route(root + "/events/<id>", methods=["GET", "POST"])
def event(id):
    if request.method == "GET":
        return redis.get("event-" + id)
    elif request.method == "POST":
        redis.set("event-" + id, request.get_data())
    else:
        return {}, 400


### Rotas

# ALL
@app.route(root + "/rotas", methods=["GET", "POST"])
def rotas():
    if request.method == "GET":
        return "Rota: List"
    elif request.method == "POST":
        return "Rota: List"
    else:
        return {}, 400


# ONE
@app.route(root + "/rotas/<id>", methods=["GET", "POST"])
def rota(id):
    if request.method == "GET":
        return redis.get("rota-" + id)
    elif request.method == "POST":
        redis.set("rota-" + id, request.get_data())
    else:
        return {}, 400


### People

# ALL
@app.route(root + "/people", methods=["GET", "POST"])
def people():
    if request.method == "GET":
        return "Person: List"
    elif request.method == "POST":
        return "Person: List"
    else:
        return {}, 400


# ONE
@app.route(root + "/people/<id>", methods=["GET", "POST"])
def person(id):
    if request.method == "GET":
        return redis.get("person-" + id)
    elif request.method == "POST":
        redis.set("person-" + id, request.get_data())
    else:
        return {}, 400