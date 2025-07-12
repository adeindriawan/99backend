import asyncio
import json
import logging
from http import HTTPStatus
from urllib.parse import urlencode
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.httpclient import AsyncHTTPClient, HTTPClientError

tornado.options.define("port", default=8000, help="run on the given port", type=int)
tornado.options.define("debug", default=True, help="run in debug mode", type=bool)
tornado.options.define("listing_service_port", default=6000, help="listing service port", type=int)
tornado.options.define("user_service_port", default=7000, help="user service port", type=int)

http_client = AsyncHTTPClient()


class BaseHandler(tornado.web.RequestHandler):
    def write_json(self, obj, status_code=200):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_status(status_code)
        self.finish(json.dumps(obj))

    def write_error(self, status_code, **kwargs):
        reason = kwargs.get("reason", HTTPStatus(status_code).phrase)
        self.write_json({"result": False, "errors": [reason]}, status_code=status_code)

    def get_service_url(self, service: str, path: str) -> str:
        port_map = {
            "listing": tornado.options.options.listing_service_port,
            "user": tornado.options.options.user_service_port,
        }
        return f"http://localhost:{port_map[service]}{path}"


class PublicListingsHandler(BaseHandler):
    """
    GET /public-api/listings
    POST /public-api/listings
    """
    async def get(self):
        query_params = {
            "page_num": self.get_argument("page_num", "1"),
            "page_size": self.get_argument("page_size", "10"),
        }
        if self.get_argument("user_id", None):
            query_params["user_id"] = self.get_argument("user_id")

        listing_url = self.get_service_url("listing", "/listings")
        full_url = f"{listing_url}?{urlencode(query_params)}"

        try:
            listing_response = await http_client.fetch(full_url)
            data = json.loads(listing_response.body)
            listings = data.get("listings", [])

            if not listings:
                return self.write_json({"result": True, "listings": []})

            user_ids = {l["user_id"] for l in listings}
            user_url_base = self.get_service_url("user", "/users/")
            
            user_tasks = [http_client.fetch(f"{user_url_base}{uid}") for uid in user_ids]
            user_responses = await asyncio.gather(*user_tasks, return_exceptions=True)

            users_map = {}
            for res in user_responses:
                if isinstance(res, HTTPClientError):
                    logging.warning(f"Could not fetch a user. Status: {res.code}, Response: {res.response.body if res.response else 'N/A'}")
                    continue
                if isinstance(res, Exception):
                    logging.error(f"Error fetching user: {res}")
                    continue
                    
                user_data = json.loads(res.body).get("user")
                if user_data:
                    users_map[user_data["id"]] = user_data

            for listing in listings:
                listing["user"] = users_map.get(listing["user_id"])
                del listing["user_id"]

            self.write_json({"result": True, "listings": listings})

        except HTTPClientError as e:
            logging.error(f"Service communication error: {e}")
            self.write_error(e.code, reason=f"Upstream service error: {e.response.body if e.response else e.message}")
        except Exception as e:
            logging.error(f"Internal error on getting listings: {e}")
            self.write_error(500, reason="An internal server error occurred.")

    async def post(self):
        try:
            body = json.loads(self.request.body)
            post_data = urlencode(body)
            url = self.get_service_url("listing", "/listings")
            
            response = await http_client.fetch(url, method="POST", body=post_data)
            
            self.write_json(json.loads(response.body), status_code=response.code)

        except json.JSONDecodeError:
            self.write_error(400, reason="Invalid JSON format.")
        except HTTPClientError as e:
            logging.error(f"Listing service communication error: {e}")
            self.write_error(e.code, reason=f"Listing service error: {e.response.body if e.response else e.message}")
        except Exception as e:
            logging.error(f"Internal error on creating listing: {e}")
            self.write_error(500, reason="An internal server error occurred.")


class PublicUsersHandler(BaseHandler):
    """
    POST /public-api/users
    """
    async def post(self):
        try:
            body = json.loads(self.request.body)
            name = body.get("name")
            if not name:
                return self.write_error(400, reason="JSON body must contain a 'name' key.")

            post_data = urlencode({"name": name})
            url = self.get_service_url("user", "/users")
            
            response = await http_client.fetch(url, method="POST", body=post_data)
            self.write_json(json.loads(response.body), status_code=response.code)

        except json.JSONDecodeError:
            self.write_error(400, reason="Invalid JSON format.")
        except HTTPClientError as e:
            logging.error(f"User service communication error: {e}")
            self.write_error(e.code, reason=f"User service error: {e.response.body if e.response else e.message}")
        except Exception as e:
            logging.error(f"Internal error on creating user: {e}")
            self.write_error(500, reason="An internal server error occurred.")


def make_app(options):
    return tornado.web.Application([
        (r"/public-api/listings", PublicListingsHandler),
        (r"/public-api/users", PublicUsersHandler),
    ], debug=options.debug)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    options = tornado.options.options

    app = make_app(options)
    app.listen(options.port)
    logging.info(f"Starting Public API layer. PORT: {options.port}, DEBUG: {options.debug}")
    logging.info(f"-> Proxying to Listing Service on port {options.listing_service_port}")
    logging.info(f"-> Proxying to User Service on port {options.user_service_port}")
    
    tornado.ioloop.IOLoop.current().start()