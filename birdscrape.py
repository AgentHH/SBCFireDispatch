#!/usr/bin/env python

import cyql
import twitter, logging
import cPickle

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

#tweets = []
#for i in range(0,1):
#    temp = twitter.get("http://api.twitter.com/1/statuses/user_timeline.json", screen_name='SBCFireDispatch', count=200, page=i)
#    tweets.extend(temp)
#cPickle.dump(tweets, open("stuff", "w"))

tweets = cPickle.load(open("stuff"))

sql = cyql.connect(dsn)

for tweet in tweets:
    # tweet['created_at']
    parsed = parse_tweet(tweet['text'])
    if parsed:
        print "Tweet!", parsed
    else:
        print "Failed!", tweet
