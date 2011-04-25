#!/usr/bin/python

import oauth2
import psycopg2
import simplejson
import urllib2

from config import *

token = oauth2.Token(key=access_token_key, secret=access_token_secret)
consumer = oauth2.Consumer(key=consumer_key, secret=consumer_secret)
signature_method = oauth2.SignatureMethod_HMAC_SHA1()

def get(url, **args):
    method = 'GET'

    parameters = args

    request = oauth2.Request.from_consumer_and_token(consumer, token=token, http_method=method, http_url=url, parameters=parameters)
    request.sign_request(signature_method, consumer, token)

    if method == "POST":
        post = request.to_postdata()
    else:
        post = None
        url = request.to_url()

    try:
        file = urllib2.urlopen(url, post)
        data = file.read()
    except urllib2.HTTPError, e:
        print e.read()
        raise e

    data = simplejson.loads(data)
    return data
