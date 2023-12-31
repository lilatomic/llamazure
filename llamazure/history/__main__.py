import os

from llamazure.history.data import TSDB, DB

if __name__ == "__main__":
	tsdb = TSDB(connstr=os.environ.get("connstr"))
	db = DB(tsdb)

	db.create_tables()
