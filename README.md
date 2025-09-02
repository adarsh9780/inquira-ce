# kill program running on a particular port

lsof -ti :8000 | xargs kill -TERM

# Inquira

A FastAPI-based API that integrates with Google Gemini LLM for conversational AI capabilities.

## Features

- RESTful API for chat interactions
- Google Gemini LLM integration
- Automatic API documentation with Swagger UI
- Error handling and graceful degradation
- Configurable system instructions and models

## Setup

### Prerequisites

- Python 3.11+
- Google AI API key

### Installation

1. Clone the repository and navigate to the project directory
2. Install dependencies using uv:

   ```bash
   uv sync
   ```

3. Create a `.env` file with your Google AI API key:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API key:

   ```
   GOOGLE_API_KEY=your_actual_api_key_here
   ```

## Usage

### Starting the API Server

Run the API server:

```bash
uv run python -m src.inquira.main
```

The API will be available at `http://localhost:8000`

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

Send a chat message to the LLM.

**Request Body:**

```json
{
  "message": "Hello, how are you?",
  "system_instruction": "You are a helpful AI assistant.",
  "model": "gemini-2.5-flash"
}
```

**Parameters:**

- `message` (required): The user's message
- `system_instruction` (optional): Custom system instruction for the chat session
- `model` (optional): LLM model to use (defaults to "gemini-2.5-flash")

**Response:**

```json
{
  "response": "Hello! I'm doing well, thank you for asking. How can I help you today?",
  "model": "gemini-2.5-flash"
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
