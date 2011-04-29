from flask import Flask, render_template, url_for, request
import cyql
import pprint
from config import dsn
import json
import dateutil.parser

app = Flask(__name__)

max_records = 100

class ISODateEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

def json_success(data):
    data['status'] = 1

    return json.dumps(data, cls=ISODateEncoder)

def json_error(error=None):
    ret = {'status': 0}
    if error:
        ret['error'] = error

    return json.dumps(ret)

def do_search(params):
    sql = cyql.connect(dsn)

    return params.do_query(sql)

@app.route('/')
def main_page():
    return render_template("map.html")

@app.route('/api/search')
def event_search():
    class SearchParameters(object):
        eventtype = None
        count = 25
        location = None
        radius = None
        startdate = None
        enddate = None
        order = 'asc'

        def set_count(self, count):
            self.count = max(min(count, max_records), 1)
            return True

        def set_eventtype(self, eventtype):
            self.eventtype = eventtype
            return True

        def set_location(self, locationstring):
            coords = [double(x) for x in locationstring.split(",")]
            if len(coords) != 2:
                return False
            self.coords = coords
            return True

        def set_radius(self, radius):
            self.radius = radius
            return True

        def set_startdate(self, startdate):
            self.startdate = dateutil.parser.parse(qs['startdate'])
            if not self.startdate:
                return False
            self.startdate = self.startdate.isoformat()
            return True

        def set_enddate(self, enddate):
            self.enddate = dateutil.parser.parse(qs['enddate'])
            if not self.enddate:
                return False
            self.enddate = self.enddate.isoformat()
            return True

        def set_order(self, order):
            order = order.strip().lower()
            if order == 'asc':
                self.order = 'asc'
            elif order == 'desc':
                self.order = 'desc'
            else:
                return False
            return True

        def do_query(self, sql):
            query = ["select address, city, url, type, location, time from events"]

            where = []
            if self.eventtype:
                where.append("type = %{self.eventtype}s")
            if self.startdate:
                where.append("time >= %{self.startdate}s")
            if self.enddate:
                where.append("time <= %{self.enddate}s")
            if len(where) < 1:
                return None
            query.append("where " + " and ".join(where))

            if self.order:
                query.append("order by time %s" % (self.order))

            query.append("limit %{self.count}s")

            return sql.all(" ".join(query))

    qs = request.args

    if len(qs) < 1:
        return json_error("can't search with no parameters")

    params = SearchParameters()

    if 'count' in qs:
        if not params.set_count(qs['count']):
            return json_error("unable to use given count")

    if 'type' in qs:
        if not params.set_eventtype(int(qs['type'])):
            return json_error("unable to use given event type")

    if 'location' in qs:
        if not params.set_location(qs['location']):
            return json_error("unable to use given location")

    if 'radius' in qs:
        if not params.set_radius(double(qs['radius'])):
            return json_error("unable to use given radius")

    if 'startdate' in qs:
        if not params.set_startdate(qs['startdate']):
            return json_error("invalid start date")

    if 'enddate' in qs:
        if not params.set_enddate(qs['enddate']):
            return json_error("invalid end date")

    if 'order' in qs:
        if not params.set_order(qs['order']):
            return json_error("invalid order")

    try:
        events = do_search(params)
        if not events:
            return json_error("unable to complete search")

        data = []
        for event in events:
            loc = [x.strip() for x in event[4].strip('()').split(',')]
            data.append({'desc': "%s, %s" % (event[0], event[1]), 'url': event[2], 'type': event[3], 'lat': loc[0], 'long': loc[1], 'time': event[5]})
    except Exception, e:
        return json_error(str(e))

    return json_success({'returned': len(data), 'events': data})

@app.route('/api/latest')
@app.route('/api/latest/<int:count>')
def latest_events(count=25):
    if count < 1:
        return json_error("need a non-zero count")

    if count > max_records:
        count = max_records

    sql = cyql.connect(dsn)
    try:
        events = sql.all('''
            select address, city, url, type, location, time
                from events limit %(count)s
            ''')
        data = []
        for event in events:
            loc = [x.strip() for x in event[4].strip('()').split(',')]
            data.append({'desc': "%s, %s" % (event[0], event[1]), 'url': event[2], 'type': event[3], 'lat': loc[0], 'long': loc[1], 'time': event[5]})
    except Exception, e:
        return json_error(str(e))

    return json_success({'returned': len(data), 'events': data})

@app.route('/api/between/<string:start>/<string:end>')
def events_between(**args):
    start = dateutil.parser.parse(args['start']) #.isoformat()
    end = dateutil.parser.parse(args['end']) #.isoformat()

    if not start and not end:
        return json_error("both dates are malformed")
    elif not start:
        return json_error("start date is malformed")
    elif not end:
        return json_error("end date is malformed")
    elif start > end:
        return json_error("start is after end")
    
    count = max_records

    sql = cyql.connect(dsn)
    try:
        events = sql.all('''
            select address, city, url, type, location, time
                from events
                where time > %(start)s and time < %(end)s
                limit %{max_records}s
            ''')
        data = []
        for event in events:
            loc = [x.strip() for x in event[4].strip('()').split(',')]
            data.append({'desc': "%s, %s" % (event[0], event[1]), 'url': event[2], 'type': event[3], 'lat': loc[0], 'long': loc[1], 'time': event[5]})
    except Exception, e:
        return json_error(str(e))

    return json_success({'returned': len(data), 'events': data})

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

    return json_success({'types': types})

if __name__ == "__main__":
    app.run(debug=True)
