# Typing Speed API

This project is a FastAPI application that provides a typing speed test via HTTP requests. Users can start a typing test and receive their typing speed in words per minute (WPM) as a response.

## Project Structure

```
typing-speed-api
├── src
│   ├── main.py               # Entry point of the FastAPI application
│   ├── api
│   │   └── v1
│   │       ├── routes.py     # API routes for the typing speed test
│   │       └── schemas.py    # Pydantic models for request and response validation
│   ├── services
│   │   └── typing_test.py     # Business logic for the typing test
│   ├── models
│   │   └── result.py          # Data model for storing typing test results
│   └── utils
│       └── timer.py           # Utility functions for timing the typing test
├── tests
│   └── test_typing_api.py     # Unit tests for the FastAPI application
├── requirements.txt            # Project dependencies
├── .gitignore                  # Files and directories to ignore by Git
└── README.md                   # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd typing-speed-api
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```
   uvicorn src.main:app --reload
   ```

## Usage

- To start a typing test, send a POST request to the `/start_typing_test` endpoint.
- The response will include the typing speed in words per minute (WPM).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.