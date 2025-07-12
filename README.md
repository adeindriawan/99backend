# Real Estate Microservices System

This project is a technical assignment demonstrating a microservices architecture for a real estate platform. The system is composed of three independent Python web applications built with the Tornado framework.

## Architecture

The system comprises three distinct microservices:

1.  **Listing Service** (`listing_service.py`)
    * Manages all information about properties available for rent or sale.
    * Communicates with its own SQLite database (`listings.db`).
    * Runs on `http://localhost:6000`.

2.  **User Service** (`user_service.py`)
    * Manages all user information.
    * Communicates with its own SQLite database (`users.db`).
    * Runs on `http://localhost:7000`.

3.  **Public API Layer** (`public_api.py`)
    * Acts as the single entry point for external clients (e.g., a mobile app or website).
    * It does not have its own database. Instead, it fetches and aggregates data by making API calls to the Listing and User services.
    * Runs on `http://localhost:8000`.

---

## Prerequisites

* Python 3
* `pip` for package management
* `virtualenv` for creating isolated Python environments (though for this assignment, I am using venv)

---

## Setup Instructions

Follow these steps to set up and run the project on your local machine.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-folder>
````

### 2\. Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

```bash
# Create the virtual environment
# Replace 'python3' with 'python' if that is your command for Python 3
virtualenv env --python=python3

# Activate the environment
# On macOS/Linux:
source env/bin/activate

# On Windows (yep, I am using Windows machine for this):
.\env\Scripts\activate
```

You will see `(env)` at the beginning of your command line prompt once it's activated.

### 3\. Install Dependencies

Install the required Python libraries using the provided `requirements.txt` file (I am using requirements.txt, not python-libs.txt just because it's more common).

```bash
pip install -r requirements.txt
```

-----

## Running the Services

You must run each of the three services in a **separate terminal window**.

### Terminal 1: Start the Listing Service

```bash
# Make sure your virtual environment is active
python listing_service.py --port=6000
```

*Output should indicate the service is running on port 6000.*

### Terminal 2: Start the User Service

```bash
# Make sure your virtual environment is active
python user_service.py --port=7000
```

*Output should indicate the service is running on port 7000. This will create a `users.db` file.*

### Terminal 3: Start the Public API Layer

```bash
# Make sure your virtual environment is active
python public_api.py --port=8000 --listing-service-port=6000 --user-service-port=7000
```

*Output should indicate the service is running on port 8000 and proxying to the other services.*

At this point, all three microservices are running and ready to accept requests.

-----

## Testing with cURL

All interactions from an external client should go through the **Public API Layer** on port `8000`.

### 1\. Create a New User

This request is sent to the Public API, which forwards it to the User Service.

**macOS/Linux:**

```bash
curl -X POST http://localhost:8000/public-api/users \
-H "Content-Type: application/json" \
-d '{"name": "Siti"}'
```

**Windows (cmd.exe):**

```bash
curl -X POST http://localhost:8000/public-api/users -H "Content-Type: application/json" -d "{\"name\": \"Siti\"}"
```

*You should receive a successful response containing the new user's details, including their `id`.*

### 2\. Create a New Listing

Use the `user_id` from the previous step to create a listing. This request is sent to the Public API, which forwards it to the Listing Service.

**macOS/Linux:**

```bash
curl -X POST http://localhost:8000/public-api/listings \
-H "Content-Type: application/json" \
-d '{
    "user_id": 1,
    "listing_type": "rent",
    "price": 5000000
}'
```

**Windows (cmd.exe):**

```bash
curl -X POST http://localhost:8000/public-api/listings -H "Content-Type: application/json" -d "{\"user_id\": 1, \"listing_type\": \"rent\", \"price\": 5000000}"
```

### 3\. Get All Listings

This demonstrates the core functionality of the Public API Layer. It fetches listings, then fetches the corresponding user for each listing, and combines them into a single response.

```bash
curl "http://localhost:8000/public-api/listings"
```

The response will be a JSON object containing a list of properties, with the full user object embedded within each one, as per the assignment requirements.
