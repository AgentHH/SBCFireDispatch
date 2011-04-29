CREATE SCHEMA sbcfiredispatch
    CREATE TABLE eventtypes (id serial PRIMARY KEY, type text NOT NULL UNIQUE)
    CREATE TABLE events (id text PRIMARY KEY, address text, city text, url text, type integer REFERENCES eventtypes(id), location point NOT NULL, time timestamp NOT NULL)
;
