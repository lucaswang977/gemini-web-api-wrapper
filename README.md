# Gemini Web OpenAI API Wrapper

This project is a FastAPI server that wraps the web version of the Gemini Web API (`gemini-webapi`) to provide OpenAI-compatible API endpoints (`/v1/chat/completions` and `/v1/models`).

**This wrapper is explicitly built and optimized for [Aider](https://aider.chat/).** It allows Aider to seamlessly utilize powerful web-based Gemini models like `gemini-3-flash-thinking-plus` and `gemini-3-pro` by routing OpenAI-styled requests through this local server to the Gemini Web interface.

> **Acknowledgement:** This project is based on [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API). All the supported model definitions and constant values can be found in the repository at [constants.py](https://github.https://github.com/HanaokaYuzu/Gemini-API/blob/master/src/gemini_webapi/constants.py).

## Features

* **OpenAI Compatible Endpoints**: Implements `/v1/chat/completions` for chat completions and `/v1/models` for listing available models.
* **Reasoning/Thoughts Support**: Supports streaming and returning reasoning processes (`reasoning_content`) for models that support thinking (e.g., `gemini-3-flash-thinking-plus`).
* **Multimodal Support**: Supports base64 image data URLs in messages for vision tasks.
* **Streaming & Non-Streaming**: Supports both standard HTTP JSON responses and Server-Sent Events (SSE) streaming responses.
* **Robust Cookie Management**: Securely handles Web Gemini session cookies with automatic initialization checks and failure alerts during startup.
* **Docker Ready**: Fully containerized and ready for rapid deployment.

## Prerequisites

To use this wrapper, you need to extract the session cookies from your browser where you are logged into Gemini (Google AI).

* `SECURE_1PSID`
* `SECURE_1PSIDTS`

## Installation & Running

### Using Docker (Recommended)

1. **Build the Docker Image:**
   ```bash
   docker build -t gemini-openai-wrapper .
   ```

2. **Run the Container:**
   Pass your cookies as environment variables. You can run the container in either foreground mode or background mode.

   #### Option A: Foreground Running Mode (Interactive with automatic cleanup)
   Ideal for viewing real-time logs directly in your terminal. The container is automatically removed when stopped.
   ```bash
   docker run --rm -it \
     -p 6969:6969 \
     -e SECURE_1PSID="your_secure_1psid_value" \
     -e SECURE_1PSIDTS="your_secure_1psidts_value" \
     --name gemini-wrapper \
     gemini-openai-wrapper
   ```

   #### Option B: Background Running Mode (Detached)
   Ideal for running the service persistently in the background.
   ```bash
   docker run -d \
     -p 6969:6969 \
     -e SECURE_1PSID="your_secure_1psid_value" \
     -e SECURE_1PSIDTS="your_secure_1psidts_value" \
     --name gemini-wrapper \
     gemini-openai-wrapper
   ```

### Local Development

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables:**
   ```bash
   export SECURE_1PSID="your_secure_1psid_value"
   export SECURE_1PSIDTS="your_secure_1psidts_value"
   ```

3. **Run the Server:**
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:6969`.

## API Endpoints

### 1. List Models
* **URL:** `/v1/models`
* **Method:** `GET`
* **Response:** Returns the list of supported models.

### 2. Chat Completions
* **URL:** `/v1/chat/completions`
* **Method:** `POST`
* **Payload Structure:** Compatible with the standard OpenAI chat completion payload (supports `model`, `messages`, and `stream`).

## Usage with Aider

You can easily use this wrapper with **Aider** by routing OpenAI requests to your local server instance. Since the server mimics OpenAI, you need to configure the base URL and pass a placeholder API key.

### Configuration Examples

#### Example 1: Running with gemini-3-flash-thinking-plus (Recommended for coding)
To take advantage of the thinking capabilities, you can specify the model directly with environment variables:

```bash
export OPENAI_API_BASE="http://localhost:6969/v1"
export OPENAI_API_KEY="any-dummy-string"

aider --model openai/gemini-3-flash-thinking-plus
```

#### Example 2: Running with gemini-3-pro
Alternatively, you can run Aider using the `gemini-3-pro` model:

```bash
export OPENAI_API_BASE="http://localhost:6969/v1"
export OPENAI_API_KEY="any-dummy-string"

aider --model openai/gemini-3-pro
```

#### Example 3: One-liner Command
You can also pass the configurations directly when running the command:

```bash
OPENAI_API_BASE="http://localhost:6969/v1" OPENAI_API_KEY="dummy" aider --model openai/gemini-3-flash-thinking-plus
```

### Enabling Vision Support (Important for Image Recognition)

By default, Aider may not know that these custom OpenAI-compatible models support vision capabilities. If you want Aider to accept and process images using the Gemini models, you **must** configure Aider's model metadata.

Create or update the configuration file in your home directory at `$HOME/.aider.model.metadata.json` with the following content:

```json
{
  "openai/gemini-3-flash-thinking-plus": {
    "supports_vision": true
  },
  "openai/gemini-3-pro": {
    "supports_vision": true
  }
}
```

This configuration explicitly instructs Aider that these models can handle multimodal inputs (images), allowing you to seamlessly use vision features during your coding sessions.

## Project Structure

* `main.py` - The FastAPI application containing the endpoint logic, request handling, streaming implementation, and client initialization.
* `Dockerfile` - Multi-stage deployment configuration based on a slim Python 3.11 environment.
* `requirements.txt` - Project dependencies including `fastapi`, `uvicorn`, and `gemini-webapi`.

## Disclaimer

This project and this method of utilizing the Gemini API are not officially permitted or endorsed by Google. This tool is intended for personal development and educational purposes only. Please use this service as a personal behavior and at your own risk. The maintainers are not responsible for any account suspensions or consequences resulting from the use of this project.
