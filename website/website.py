from flask import Flask
import cyql
import pprint
from config import dsn
import json
import dateutil.parser

app = Flask(__name__)

class ISODateEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

def json_success(data):
    ret = {'status': 1,
            'data': data}

    return json.dumps(ret, cls=ISODateEncoder)

def json_error(error=None):
    ret = {'status': 0}
    if error:
        ret['error'] = error

    return json.dumps(ret)

@app.route('/')
def main_page():
    return "Nothing to see here, move along..."

@app.route('/api/latest')
@app.route('/api/latest/<int:count>')
def latest_events(count=25):
    sql = cyql.connect(dsn)
    try:
        events = sql.all('''
            select address, city, url, type, location, time
                from events limit %(count)s
            ''')
        data = []
        for event in events:
            loc = [x.strip() for x in event[4].strip('()').split(',')]
            data.append({'name': "%s, %s" % (event[0], event[1]), 'url': event[2], 'type': event[3], 'lat': loc[0], 'long': loc[1], 'time': event[5]})
    except Exception, e:
        return json_error(str(e))

    return json_success(data)

@app.route('/api/between/<string:start>/<string:end>')
def events_between(**args):
    start = dateutil.parser.parse(args['start'])
    end = dateutil.parser.parse(args['end'])

    if not start and not end:
        return json_error("both dates are malformed")
    elif not start:
        return json_error("start date is malformed")
    elif not end:
        return json_error("end date is malformed")

    return json_success({'startdate': start, 'enddate': end})

@app.route('/api/eventtypes')
def event_types():
    sql = cyql.connect(dsn)
    types = {}
    try:
        data = sql.all('''
            select id, type from eventtypes
            ''')
        for item in data:
            if item[0] in types:
                return json_error("error when making type list")
            types[item[0]] = item[1]
    except Exception, e:
        return json_error(str(e))

    return json_success(types)

if __name__ == "__main__":
    app.run(debug=True)
