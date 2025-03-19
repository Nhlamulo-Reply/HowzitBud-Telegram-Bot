import  mysql.connector
from Exceptions import *
from mysql.connector import errorcode

class Database:
    def __init__(self,host,user,password,database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                print("Connected to MySQL database")
        except AuthenticationError as err:
            raise AuthenticationError("Not connected to MySQL")

     #Call this function when trying to execute any query
    def execute(self,sql,params=None):
        if self.connection:
            cursor = self.connection.cursor()
            try:
                cursor.execute(sql, params)
                self.connection.commit()
            except AuthenticationError as err:
                raise AuthenticationError(f"Failed to execute query : {err}")

    def close_connection(self):
        if self.connection:
            self.connection.close()
            print("Connection closed")