from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future_builtins import ascii, filter, hex, map, oct, zip

import inspect
import os

from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

class connect(object):
    def __init__(self, dsn):
        attempt = 0
        while True:
            try:
                self.driver = psycopg2.connect(**dsn)
                break
            except psycopg2.OperationalError, e:
                if attempt == 2:
                    raise e
                attempt = attempt + 1

        try:
            self.driver.set_client_encoding('UNICODE')
            self.driver.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except:
            self.driver.close()

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @contextmanager
    def cursor(self):
        cursor = self.driver.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def execute(self, statement, depth=0, context=None):
        # two frames, accounting for execute() and @contextmanager
        frame = inspect.currentframe(depth + 2)

        with self.cursor() as cursor:
            f_globals = None
            f_locals = frame.f_locals

            if context == None:
                context = dict(**f_locals)

            start = 0
            while True:
                percent = statement.find('%', start)
                if percent == -1:
                    break

                next = statement[percent + 1]
                if next == '(':
                    start = statement.index(')', percent + 2) + 2
                    assert statement[start - 1] == 's'
                elif next == '{':
                    start = statement.index('}', percent + 2)
                    assert statement[start + 1] == 's'
                    code = statement[percent + 2:start]

                    if f_globals == None:
                        f_globals = frame.f_globals

                    key = '__cyql__%i' % (percent,)
                    # XXX: compile() in the frame's context
                    context[key] = eval(code, f_globals, f_locals)

                    statement = '%s%%(%s)%s' % (statement[0:percent], key, statement[start + 1:])
                    start = percent + len(key) + 4
                elif next in ('%', 's'):
                    start = percent + 2
                else:
                    assert False

            cursor.execute(statement, context)

            del context
            del f_locals
            del f_globals

            yield cursor

    @contextmanager
    def transact(self, synchronous_commit=True):
        self.driver.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        try:
            with self.cursor() as cursor:
                if not synchronous_commit:
                    cursor.execute('set local synchronous_commit = off')

            yield
            self.driver.commit()
        except:
            self.driver.rollback()
            raise
        finally:
            self.driver.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    def one_(self, statement, context=None):
        with self.execute(statement, 2, context) as cursor:
            one = cursor.fetchone()
            if one == None:
                return None

            assert cursor.fetchone() == None
            return one

    def __call__(self, procedure, *parameters):
        with self.execute(statement, 1) as cursor:
            return cursor.callproc(procedure, *parameters)

    def run(self, statement, context=None):
        with self.execute(statement, 1, context) as cursor:
            return cursor.rowcount

    @contextmanager
    def set(self, statement):
        with self.execute(statement, 1) as cursor:
            yield cursor

    def all(self, statement):
        with self.execute(statement, 1) as cursor:
            return cursor.fetchall()

    def one(self, statement, context=None):
        return self.one_(statement, context)

    def has(self, statement):
        exists, = self.one_('select exists(%s)' % (statement,))
        return exists

def connected(dsn):
    def wrapped(method):
        def replaced(*args, **kw):
            with connect(dsn) as sql:
                return method(*args, sql=sql, **kw)
        return replaced
    return wrapped

@contextmanager
def transact(dsn, *args, **kw):
    with connect(dsn) as connection:
        with connection.transact(*args, **kw):
            yield connection

"""
def slap_(sql, table, keys, values, path):
    csr = sql.cursor()
    try:
        csr.execute('savepoint iou')
        try:
            both = dict(keys, **values)
            fields = both.keys()

            csr.execute('''
                insert into %s (%s) values (%s)
            ''' % (
                table,
                ', '.join(fields),
                ', '.join(['%s' for key in fields])
            ), both.values())
        except psycopg2.IntegrityError, e:
            csr.execute('rollback to savepoint iou')

            csr.execute('''
                update %s set %s where %s
            ''' % (
                table,
                ', '.join([
                    key + ' = %s'
                for key in values.keys()]),
                ' and '.join([
                    key + ' = %s'
                for key in keys.keys()])
            ), values.values() + keys.values())

        return path_(csr, path)
    finally:
        csr.close()
"""
