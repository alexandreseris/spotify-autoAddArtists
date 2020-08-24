import sqlite3
import os


class Database():
    def __init__(self, dbFilePath, dbSchema, indexLs=[]):
        self.dbFilePath = os.path.abspath(dbFilePath)
        self.dbSchema = dbSchema
        self.indexLs = indexLs
        self.initialiseDb()

    def initialiseDb(self):
        if not os.path.isfile(self.dbFilePath):
            print("DATABASE CREATION {}".format(self.dbFilePath))
            self.connect()
            for statment in self.dbSchema:
                try:
                    self.execute(statment)
                except sqlite3.OperationalError:
                    pass
            self.commit()
            self.close()

    def dropDatabase(self):
        try:
            print("DROPPING DATABASE {}".format(self.dbFilePath))
            os.remove(self.dbFilePath)
        except os.error:
            input(
                "databse file is currently beeing used, please shut down every connection"
            )
            os.remove(self.dbFilePath)
        self.initialiseDb()

    def connect(self):
        print("DATABSE CONNECTION {}".format(self.dbFilePath))
        self.conn = sqlite3.connect(self.dbFilePath)
        self.cur = self.conn.cursor()

    def execute(self, req, values=None):
        if values is None:
            try:
                self.cur.execute(req)
            except Exception as err:
                print("request\n" + req + "\ncrashed")
                raise err
        else:
            try:
                self.cur.execute(req, values)
            except Exception as err:
                print("request\n" + req + "\ncrashed with values " +
                      str(values))
                raise err

    def removeIndexes(self):
        print("deleting indexes")
        for ind in self.indexLs:
            try:
                self.execute("DROP INDEX " + ind["name"] + ";")
            except sqlite3.OperationalError:
                pass
        self.commit()

    def addIndexes(self):
        print("adding indexes")
        for ind in self.indexLs:
            self.execute("CREATE INDEX " + ind["name"] + " ON " + ind["def"] +
                         ";")
        self.commit()

    def insert(self, table, values):
        replaceValuesExpr = "(" + (len(values) * "?, ")[0:-2] + ")"
        self.execute(
            "insert into {} values {}; ".format(table, replaceValuesExpr),
            values)

    def insertYolo(self, table, values):
        try:
            self.insert(table, values)
        except sqlite3.IntegrityError as err:
            print(
                str(err) + "   on table " + str(table) + ", values: " +
                str(values))

    def select(self, req):
        self.execute(req)
        return self.cur.fetchall()

    def delete(self, req):
        self.execute(req)

    def update(self, req):
        self.execute(req)

    def getChanges(self):
        # no real point since it get the number of lines affected by the last request and not by the last commit
        res = self.select("select changes() as c;")
        try:
            print("lines changed: " + str(res[0][0]))
        except:
            pass

    def commit(self, verbose=False):
        self.conn.commit()
        if verbose:
            self.getChanges()

    def rollback(self):
        self.conn.rollback()

    def formatSqlString(self, stringParam):
        return "'" + stringParam.replace("'", "''") + "'"

    def close(self):
        self.cur.close()
        self.conn.close()
