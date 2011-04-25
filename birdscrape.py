#!/usr/bin/env python

import cyql, psycopg2
import twitter, logging
import cPickle
import time

from config import dsn

def parse_location(rawlatitude, rawlongitude):
    def garbage_to_string(rawstring):
        try:
            string = rawstring.translate(None, ' ')
            string = "%s.%s" % (string[:-6], string[-6:])
            num = float(string) # just makes sure it's a real number
            return string
        except Exception, e:
            #print "Unable to convert garbage: %s" % (e)
            return None
        
    latitude = garbage_to_string(rawlatitude)
    if not latitude:
        #print "Invalid latitude"
        return None

    longitude = garbage_to_string(rawlongitude)
    if not longitude:
        #print "Invalid longitude"
        return None

    return (latitude, longitude)

def parse_tweet(text):
    elements = text.split(" *** ")
    if len(elements) != 5:
        #print "found %d elements" % (len(elements))
        return None

    (address, city, event, latitude, longitude) = elements

    loc = parse_location(latitude, longitude)

    address = address.lstrip("0 ") # get rid of annoying "0 Ucen Rd"

    return (address, city, loc, event)

def eat_tweets(tweets, rejects):
    for tweet in tweets:
        try:
            address, city, loc, event = parse_tweet(tweet['text'])
            location = ",".join(loc)
            tweetid = tweet['id_str']
            timestamp = tweet['created_at']
            url = "http://twitter.com/%s/status/%s" % (tweet['user']['screen_name'], tweetid)

            eventtype = sql.all('''
                select id from eventtypes where type = %(event)s
                    ''')
            if len(eventtype) != 0:
                (eventtype,), = eventtype
            else:
                (eventtype,), = sql.all('''
                    insert into eventtypes (type) VALUES (%(event)s) RETURNING id
                        ''')

            try:
                sql.run('''
                    insert into events (id, address, city, url, type, location, time)
                        VALUES (%(tweetid)s, %(address)s, %(city)s, %(url)s, %(eventtype)s, %(location)s, %(timestamp)s)
                        ''')
            except psycopg2.IntegrityError:
                pass
        except Exception, e:
            print e
            rejects.append(tweet)

if __name__ == "__main__":
    sql = cyql.connect(dsn)

    rejects = []
    for i in range(0,16):
        try:
            tweets = twitter.get("http://api.twitter.com/1/statuses/user_timeline.json", screen_name='SBCFireDispatch', count=200, page=i)
            eat_tweets(tweets, rejects)
        except Exception, e:
            print e
        time.sleep(15)
    cPickle.dump(rejects, open("rejects", "w"))

    #tweets = cPickle.load(open("stuff"))

