import json
import unittest
from urllib.parse import urlencode
import time

from tornado.testing import AsyncHTTPTestCase

from user_service import App as UserApp
from user_service import UsersHandler, UserHandler


class TestUserService(AsyncHTTPTestCase):
    """
    Test suite for the User Service endpoints.
    """

    def get_app(self):
        """
        This method is required by AsyncHTTPTestCase.
        It sets up the application instance for testing.
        """
        handlers = [
            (r"/users", UsersHandler),
            (r"/users/(\d+)", UserHandler),
        ]
        app = UserApp(handlers, db_name=":memory:")
        return app

    def test_1_create_user(self):
        """
        Tests the successful creation of a new user.
        """
        user_data = {"name": "Test User"}
        body = urlencode(user_data)
        response = self.fetch("/users", method="POST", body=body)
        self.assertEqual(response.code, 201)
        response_body = json.loads(response.body)
        self.assertTrue(response_body["result"])
        self.assertEqual(response_body["user"]["name"], "Test User")
        self.assertEqual(response_body["user"]["id"], 1)

    def test_2_get_user_by_id(self):
        """
        Tests fetching a single, existing user by their ID.
        """
        self.fetch("/users", method="POST", body=urlencode({"name": "Another User"}))
        response = self.fetch("/users/1")
        self.assertEqual(response.code, 200)
        response_body = json.loads(response.body)
        self.assertTrue(response_body["result"])
        self.assertEqual(response_body["user"]["id"], 1)
        self.assertEqual(response_body["user"]["name"], "Another User")

    def test_3_get_all_users(self):
        """
        Tests fetching the list of all users.
        """
        # Create a couple of users to ensure the list is not empty
        self.fetch("/users", method="POST", body=urlencode({"name": "User A"}))
        
        # Add a small delay to ensure different timestamps ---
        time.sleep(0.01)
        
        self.fetch("/users", method="POST", body=urlencode({"name": "User B"}))

        # Fetch the list
        response = self.fetch("/users")

        # Check the response
        self.assertEqual(response.code, 200)
        response_body = json.loads(response.body)

        self.assertTrue(response_body["result"])
        self.assertIsInstance(response_body["users"], list)
        self.assertEqual(len(response_body["users"]), 2)
        self.assertEqual(response_body["users"][0]["name"], "User B") # Sorted by date desc

    def test_4_get_nonexistent_user(self):
        """
        Tests that fetching a user with an ID that does not exist returns a 404 error.
        """
        response = self.fetch("/users/999")
        self.assertEqual(response.code, 404)
        response_body = json.loads(response.body)
        self.assertFalse(response_body["result"])
        self.assertIn("not found", response_body["errors"][0])


if __name__ == '__main__':
    unittest.main()