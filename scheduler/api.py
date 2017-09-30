from flask import Flask
from redis import Redis

app = Flask(__name__)
redis = Redis(host='redis', port=6379)

root = "/api/1.0"

@app.route('/')
def hello():
    count = redis.incr('hits')
    return 'Hello World! I have been seen {} times.\n'.format(count)


@app.route(root + "/events")
def events():
    return "Event List"


@app.route(root + "/rotas")
def rotas():
    return "Rota List"


@app.route(root + "/people")
def people():
    return "Person List"