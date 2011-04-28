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

    return json.dumps(data, cls=ISODateEncoder)

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
        data = sql.all('''
            select address, city, url, type, location, time
                from events limit %(count)s
            ''')
    except:
        return json_error()

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

if __name__ == "__main__":
    app.run(debug=True)
