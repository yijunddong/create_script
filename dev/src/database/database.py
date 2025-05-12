import duckdb


def get_db_file():
    conn= duckdb.connect(database='dev/data/database.duckdb')
    return conn

def get_db_memory():
    conn= duckdb.connect()
    return conn



def close_db(conn):
    conn.close()



