import os
import psycopg


def get_conn():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3)