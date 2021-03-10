import logging
import os
from common import secrets_manager
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

logger = logging.getLogger()
logger.setLevel(logging.INFO)
pg_pool = None


def get_connection(autocommit, dbname):

    return get_connection_with_secret_name(autocommit, dbname, "secret_name")


def get_connection_with_secret_name(autocommit, dbname, secret_name_param):
    try:
        secret_name = os.environ.get(secret_name_param)
        db_connection_obj = secrets_manager.get_secret(secret_name)
        return get_connection_with_secret(autocommit, dbname, db_connection_obj)

    except Exception as e:
        logger.error(str(e))
        raise e


def get_connection_with_secret(autocommit, dbname, db_connection_obj):

    try:
        PWD = db_connection_obj["password"]
        USR = db_connection_obj["username"]
        ENDPOINT = db_connection_obj["proxy"]
        PORT = db_connection_obj["port"]
        DBNAME = dbname

        conn = psycopg2.connect(host=ENDPOINT, database=DBNAME,
                                user=USR, password=PWD,
                                port=PORT)

        conn.autocommit = autocommit
        return conn

    except Exception as e:
        logger.error("ERROR: Could not connect to Postgres instance.")
        logger.error(str(e))
        raise e


def query_object(connection, logger, sql, keys):
    try:
        with connection.cursor() as cur:
            cur.execute(sql, keys)
            if not cur:
                return None
            result = cur.fetchone()
            if not result:
                return None
            return result[0]

    except Exception as e:
        logger.error('Exception at sql=%s ; Exception=%s' % (sql, e))
        raise e


def execute(connection, logger, sql, keys):
    try:
        with connection.cursor() as cur:
            cur.execute(sql, keys)

    except Exception as e:
        logger.error('Exception at sql=%s ; Exception=%s' % (sql, e))
        raise e


def query_all(connection, logger, sql, keys, ):
    try:
        with connection.cursor() as cur:
            cur.execute(sql, keys)
            return cur.fetchall()

    except Exception as e:
        logger.error('Exception at sql=%s ; Exception=%s' % (sql, e))
        raise e


def query_all_RealDictCursor(connection, logger, sql, keys):
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, keys)
            return cur.fetchall()

    except Exception as e:
        logger.error('Exception at sql=%s ; Exception=%s' % (sql, e))
        raise e


def close_conn(con):
    global pg_pool
    if pg_pool is not None:
        pg_pool.putconn(con)


def get_conn_from_pool():
    global pg_pool
    if pg_pool is not None:
        return pg_pool.getconn()




