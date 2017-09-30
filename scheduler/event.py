from redis import Redis

class Event:
    def __init__(self, event_id, name, description, start_date, end_date, rotas):
        self.event_id = event_id
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.rotas = rotas

    def get_event(self, id):
        return "events" + id
   
class Rota:
    def __init__(self, rota_id, name, description, number_of_people_required, people):
        self.rota_id = rota_id
        self.name = name
        self.description = description
        self.number_of_people_required = number_of_people_required
        self.people = people

class Person:
    def __init__(self, person_id, name):
        self.person_id = person_id
        self.name = name


