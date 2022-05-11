# This module required for interaction with database

# todo use real database
import sqlite3
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


class DBProcessor:

    def __init__(self, db_path: str):
        try:
            self.db_connection = sqlite3.connect(db_path)
            logger.debug("Database connection successfully created")
            self.create_users_table()

        except sqlite3.Error as error:
            logger.error(f"Error while connecting to database: {error}")

    def __del__(self):
        if self.db_connection:
            self.db_connection.close()

    def create_users_table(self):
        try:
            query = "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY NOT NULL UNIQUE, username VARCHAR(20) NOT NULL, first_name VARCHAR(20), location TEXT NOT NULL)"

            cursor = self.db_connection.cursor()
            cursor.execute(query)

            logger.debug("Users table successfully created")
        except sqlite3.Error as error:
            logger.error(f"Error when trying to create users table: {error}")
        finally:
            cursor.close()

    def add_user_to_db(self, id: int, username: str, first_name: str, location: str):
        try:
            query = "INSERT INTO users (id, username, first_name, location) VALUES (?, ?, ?, ?)"

            cursor = self.db_connection.cursor()
            cursor.execute(query, [id, username, first_name, location])
            self.db_connection.commit()

            logger.debug(f"Users {username} successfully added to users table")
        except sqlite3.Error as error:
            logger.error(f"Error when trying to insert user {username} into users table: {error}")
        finally:
            cursor.close()

    def get_user_from_db(self, id: int):
        try:
            query = "SELECT * FROM users WHERE id=?"

            cursor = self.db_connection.cursor()
            cursor.execute(query, [id])
            result = cursor.fetchall()

            if result:
                return result[0]

            return
        except sqlite3.Error as error:
            logger.error(f"Error when trying to find user {id} in users table: {error}")
        finally:
            cursor.close()

