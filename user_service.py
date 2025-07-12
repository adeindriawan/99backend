import json
import logging
import sqlite3
import time
import tornado.ioloop
import tornado.options
import tornado.web
from http import HTTPStatus

tornado.options.define("port", default=7000, help="run on the given port", type=int)
tornado.options.define("debug", default=True, help="run in debug mode", type=bool)


class App(tornado.web.Application):
    def __init__(self, handlers, db_name="users.db", **kwargs):
        super().__init__(handlers, **kwargs)
        self.db = sqlite3.connect(db_name)
        self.db.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        cursor = self.db.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS 'users' ("
            + "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
            + "name TEXT NOT NULL,"
            + "created_at INTEGER NOT NULL,"
            + "updated_at INTEGER NOT NULL"
            + ");"
        )
        self.db.commit()


class BaseHandler(tornado.web.RequestHandler):
    def write_json(self, obj, status_code=200):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_status(status_code)
        self.finish(json.dumps(obj)) # Use finish() to end the request

    def write_error(self, status_code, **kwargs):
        reason = kwargs.get("reason", HTTPStatus(status_code).phrase)
        self.write_json({"result": False, "errors": [reason]}, status_code=status_code)


class UsersHandler(BaseHandler):
    """
    Handles routes for listing and creating users.
    GET /users
    POST /users
    """
    def get(self):
        """ Get all users with pagination. """
        try:
            page_num = int(self.get_argument("page_num", 1))
            page_size = int(self.get_argument("page_size", 10))
        except ValueError:
            return self.write_error(400, reason="Invalid page_num or page_size.")

        limit = page_size
        offset = (page_num - 1) * page_size
        select_stmt = "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?"
        
        cursor = self.application.db.cursor()
        results = cursor.execute(select_stmt, (limit, offset))
        
        users = []
        fields = ["id", "name", "created_at", "updated_at"]
        for row in results:
            user = {field: row[field] for field in fields}
            users.append(user)
            
        self.write_json({"result": True, "users": users})

    def post(self):
        """ Create a new user. """
        name = self.get_argument("name", None)
        if not name:
            return self.write_error(400, reason="name parameter is required.")

        time_now = int(time.time() * 1e6)
        
        try:
            cursor = self.application.db.cursor()
            cursor.execute(
                "INSERT INTO 'users' ('name', 'created_at', 'updated_at') VALUES (?, ?, ?)",
                (name, time_now, time_now),
            )
            self.application.db.commit()

            if cursor.lastrowid is None:
                return self.write_error(500, reason="Failed to create user.")

            user = {
                "id": cursor.lastrowid,
                "name": name,
                "created_at": time_now,
                "updated_at": time_now,
            }
            self.write_json({"result": True, "user": user}, status_code=201)
        except Exception as e:
            logging.error(f"Database error on user creation: {e}")
            self.write_error(500, reason="Internal server error.")


class UserHandler(BaseHandler):
    """
    Handles retrieving a single user by ID.
    GET /users/{id}
    """
    def get(self, user_id):
        try:
            user_id = int(user_id)
        except ValueError:
            return self.write_error(400, reason="Invalid user ID format.")

        cursor = self.application.db.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()

        if row:
            fields = ["id", "name", "created_at", "updated_at"]
            user = {field: row[field] for field in fields}
            self.write_json({"result": True, "user": user})
        else:
            self.write_error(404, reason=f"User with id {user_id} not found.")


def make_app(options):
    return App([
        (r"/users", UsersHandler),
        (r"/users/(\d+)", UserHandler),
    ], debug=options.debug)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    options = tornado.options.options
    
    app = make_app(options)
    app.listen(options.port)
    logging.info(f"Starting user service. PORT: {options.port}, DEBUG: {options.debug}")
    
    tornado.ioloop.IOLoop.current().start()