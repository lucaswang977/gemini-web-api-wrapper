
# Gemini Web OpenAI API Wrapper

This project is a FastAPI server that wraps the web version of the Gemini Web API (`gemini-webapi`) to provide OpenAI-compatible API endpoints (`/v1/chat/completions` and `/v1/models`).

**This wrapper is explicitly modified and optimized to work with [gptme](https://github.com/gptme/gptme) as a local terminal code agent.** By masking powerful web-based Gemini models as native OpenAI models, it tricks `gptme` into enabling advanced features like real-time streaming and multimodal vision processing without triggering client-side validation errors.

> **Acknowledgement:** This project is based on [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API). Supported model definitions and constant values originate from the base repository.

---

## Features

* **OpenAI Compatible Endpoints**: Implements `/v1/chat/completions` and `/v1/models` matching OpenAI's expected JSON specifications.
* **Faked Model Identifiers**: Masquerades Gemini models as OpenAI GPT models to bypass `gptme` feature-flag restrictions on streaming and vision capabilities.
* **Reasoning/Thoughts Extraction**: Real-time extraction of `thoughts_delta` from streaming chunks, mapping them to the standard `reasoning_content` parameter.
* **Multimodal / Vision Support**: Intercepts base64 image data URLs, writes them temporarily to disk as `.png` files for Gemini to consume, and cleans them up automatically.
* **Robust Cookie Management**: Securely initializes using Web Gemini session cookies, checking for expiration during startup to prevent silent failures.

---

## Model Mapping Schema

When `gptme` makes a request to the local proxy, the model names are mapped transparently under the hood:

| gptme Requested Model | Actual Web Gemini Target | Optimized Use Case |
| :--- | :--- | :--- |
| `openai/gpt-5-mini` <br> `gpt-5-mini` | `gemini-3-flash-thinking` | **Recommended for Dev.** Deep reasoning, multi-step planning, and fast code iterations. |
| `openai/gpt-5` <br> `gpt-5` | `gemini-3-pro` | Heavyweight architectural modifications and highly complex debugging. |

---

## Prerequisites

To authenticate the underlying browser session, grab the following cookies from your active browser session logged into Gemini:

* `SECURE_1PSID`
* `SECURE_1PSIDTS`

---

## Installation & Running

### 1. Using Docker (Recommended)

* **Build the image:**
  ```bash
  docker build -t gemini-openai-wrapper .
  ```

* **Run interactively (Foreground mode):**
  ```bash
  docker run --rm -it \
    -p 6969:6969 \
    -e SECURE_1PSID="your_secure_1psid_value" \
    -e SECURE_1PSIDTS="your_secure_1psidts_value" \
    --name gemini-wrapper \
    gemini-openai-wrapper
  ```

### 2. Local Python Setup

* **Install dependencies & set environment variables:**
  ```bash
  pip install -r requirements.txt
  export SECURE_1PSID="your_secure_1psid_value"
  export SECURE_1PSIDTS="your_secure_1psidts_value"
  ```

* **Launch the server:**
  ```bash
  python main.py
  ```
  The API will bind to `http://localhost:6969`.

---

## Integration with gptme

### Method A: One-Liner Execution (Environment Flags)
You can point `gptme` directly to the proxy on launch by passing the base URL override:

```bash
OPENAI_BASE_URL="http://localhost:6969/v1" OPENAI_API_KEY="dummy-key" gptme --model openai/gpt-5-mini
```

### Method B: Persistent Configuration (`config.toml`)
To make the integration permanent, append the configuration block below to your `gptme` configuration file (typically located at `~/.config/gptme/config.toml`):

```toml
[env]
OPENAI_BASE_URL = "http://localhost:6969/v1"
MODEL = "openai/gpt-5-mini"
```

Using this configuration ensures that `gptme` initializes with vision capabilities, code block rendering, and text streaming automatically activated.

---

## Project Structure

* `main.py` - Core FastAPI handling, endpoint translation, image rendering buffers, and streaming generator loops.
* `Dockerfile` - Multi-stage deployment recipe based on a clean Python 3.11 image.
* `requirements.txt` - Python package requirements (`fastapi`, `uvicorn`, `gemini-webapi`, `loguru`).

---

## Disclaimer

This project acts as an unofficial bridging layer. It is neither endorsed nor supported by Google. Use this adapter responsibly, for personal development, and educational exploration only.

