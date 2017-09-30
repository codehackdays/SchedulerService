from flask import Flask
from redis import Redis

app = Flask(__name__)
redis = Redis(host='redis', port=6379)

root = "/api/1.0"


@app.route('/')
def hello():
    count = redis.incr('hits')
    return 'Hello World! I have been seen {} times.\n'.format(count)


#GET ALL
@app.route(root + "/events")
def events():
    return "Event: List"


#GET ONE
@app.route(root + "/events/<id>")
def event(id):
    return "Event: " + id


#GET ALL
@app.route(root + "/rotas")
def rotas():
    return "Rota: List"


#GET ONE
@app.route(root + "/rotas/<id>")
def rota(id):
    return "Rota: " + id


#GET ALL
@app.route(root + "/people")
def people():
    return "Person: List"


#GET ONE
@app.route(root + "/people/<id>")
def person(id):
    return "Person: " + id