# Inquira

A FastAPI-based API that integrates with Google Gemini LLM for conversational AI capabilities.

## Setup

### Prerequisites

- Python 3.12+
- Google Gemini API key

## Alternative Installation Methods

If you prefer not to use UV, you can install and run the application using pip or run it directly with Python:

### Using pip

1. Install the package in development mode:

```bash
pip install -e .
```

2. Run the application:

```bash
inquira
```

### Direct Python Execution

You can also run the application directly without installation:

```bash
python -m src.inquira.main
```

**Note:** When running directly with Python, make sure all dependencies are installed:

```bash
pip install -r requirements.txt
```

## Usage

### Starting the API Server

Run the API server:

```bash
uv run python -m src.inquira.main
```

The API will be available at `http://localhost:8000`

### Launching the GUI

The application includes a web-based GUI that can be accessed at `http://localhost:8000/ui` after starting the server. The server will automatically open your default web browser to the GUI when launched.

### API Endpoints

#### GET /

Returns basic API information.

**Response:**

```json
{
  "message": "Inquira is running",
  "version": "1.0.0"
}
```

#### POST /chat

Send a chat message to the LLM for data analysis.

**Request Body:**

```json
{
  "question": "What is the average sales by region?",
  "current_code": "",
  "model": "gemini-2.5-flash",
  "context": "Sales data analysis"
}
```

**Parameters:**

- `question` (required): The data analysis question
- `current_code` (optional): Existing Python code to build upon
- `model` (optional): LLM model to use (defaults to "gemini-2.5-flash")
- `context` (optional): Additional context about the data

**Response:**

```json
{
  "is_safe": true,
  "is_relevant": true,
  "code": "import pandas as pd\n# Analysis code here",
  "explanation": "Step-by-step explanation of the analysis"
}
```

### Authentication Endpoints

#### POST /auth/register

Register a new user account.

**Request Body:**

```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

#### POST /auth/login

Login with existing credentials.

**Request Body:**

```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

#### POST /auth/logout

Logout the current user.

#### GET /auth/verify

Verify if the current user is authenticated.

#### GET /auth/profile

Get the current user's profile information.

#### POST /auth/change-password

Change the current user's password.

#### DELETE /auth/delete-account

Permanently delete the current user's account.

### API Key Management

#### POST /set-api-key

Set the Google Gemini API key for LLM services.

**Request Body:**

```json
{
  "api_key": "your-google-gemini-api-key"
}
```

### Settings Management

#### POST /settings/create

Create or update user settings including API key, data path, and schema path.

**Request Body:**

```json
{
  "api_key": "your-api-key",
  "data_path": "/path/to/data",
  "schema_path": "/path/to/schema.json",
  "context": "Data domain context"
}
```

#### GET /settings/view

View current user settings.

#### DELETE /settings/delete

Delete all user settings.

### Data Preview Endpoints

#### GET /data/schema

Get schema information for the configured data file.

#### GET /data/preview

Get a preview of the configured data file with optional sampling type.

**Query Parameters:**

- `sample_type`: "random", "first", or "last" (default: "random")

### Schema Management Endpoints

#### POST /schema/generate

Generate a schema for a data file using LLM analysis.

**Request Body:**

```json
{
  "filepath": "/path/to/data/file",
  "context": "Optional context about the data"
}
```

#### GET /schema/load/{filepath}

Load an existing schema for a data file.

#### POST /schema/save

Save a user-modified schema.

#### GET /schema/list

List all schemas for the current user.

### Code Execution Endpoints

#### POST /execute/

Execute Python code safely with security checks.

**Request Body:**

```json
{
  "code": "print('Hello, World!')"
}
```

#### POST /execute/analyze

Analyze Python code for security violations without executing it.

**Request Body:**

```json
{
  "code": "import os; os.system('ls')"
}
```

#### POST /execute/with-variables

Execute Python code and return created variables.

**Request Body:**

```json
{
  "code": "x = 42\ny = x * 2"
}
```

### API Documentation

Access the interactive API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend Integration

### JavaScript Example

```javascript
// Send a chat message
async function sendChatMessage(message) {
  const response = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: message,
      system_instruction: "You are a helpful AI assistant.",
    }),
  });

  const data = await response.json();
  return data.response;
}

// Usage
sendChatMessage("Hello!").then((response) => {
  console.log("AI Response:", response);
});
```

### React Example

```jsx
import { useState } from "react";

function ChatComponent() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!message.trim()) return;

    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: message,
          system_instruction: "You are a helpful AI assistant.",
        }),
      });

      const data = await res.json();
      setResponse(data.response);
    } catch (error) {
      setResponse("Error: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message..."
      />
      <button onClick={sendMessage} disabled={loading}>
        {loading ? "Sending..." : "Send"}
      </button>
      {response && <p>AI: {response}</p>}
    </div>
  );
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `422`: Validation error (invalid request format)
- `500`: Internal server error
- `503`: Service unavailable (LLM not configured)

## Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Your Google AI API key (required)

### Default Settings

- Default model: `gemini-2.5-flash`
- Default system instruction: `"You are a helpful AI assistant."`

## Development

### Project Structure

```
src/inquira/
├── __init__.py
├── main.py          # FastAPI application and endpoints
└── llm_service.py   # Google Gemini LLM integration
```

### Running Tests

```bash
# Install test dependencies if needed
uv add pytest

# Run tests
uv run pytest
```

## License

This project is licensed under the MIT License.
