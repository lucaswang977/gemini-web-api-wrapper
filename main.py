import os
import io
import base64
import re
import json
import time
import tempfile
from typing import Optional, Union, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger
import uvicorn
from gemini_webapi.client import GeminiClient
from gemini_webapi.constants import AccountStatus

# --- Load cookie information from environment variables ---
logger.info("Attempting to load cookie information from environment variables...")
secure_1psid = os.getenv("SECURE_1PSID")
secure_1psidts = os.getenv("SECURE_1PSIDTS")

if secure_1psid and secure_1psidts:
    logger.info("Successfully retrieved cookie information from environment variables.")
else:
    if not secure_1psid:
        logger.warning("Environment variable 'SECURE_1PSID' is not set.")
    if not secure_1psidts:
        logger.warning("Environment variable 'SECURE_1PSIDTS' is not set.")

# Initialize global client instance
logger.info("Initializing GeminiClient instance...")
client = GeminiClient(secure_1psid=secure_1psid, secure_1psidts=secure_1psidts)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from gemini_webapi.constants import AccountStatus
    
    logger.info("Application startup: Starting GeminiClient.init().")
    try:
        try:
            await asyncio.wait_for(client.init(verbose=True), timeout=10.0)
        except asyncio.TimeoutError:
            raise RuntimeError(
                "Initialization to Gemini timed out within 10 seconds. It is highly likely that "
                "an infinite loop of automatic retries is occurring inside the library because the cookies "
                "(environment variables) have completely expired. Please set the latest cookies in the "
                "environment variables and restart."
            )
        
        if client.account_status == AccountStatus.UNAUTHENTICATED:
            error_msg = (
                "[Fatal Auth Error] Failed to log in to Gemini. The provided environment variable "
                "SECURE_1PSID or SECURE_1PSIDTS is expired or invalid. Please copy the latest values from "
                "your browser, update the environment variables, and restart the container."
            )
            logger.error(error_msg)
            await client.close()
            raise RuntimeError(error_msg)
            
        logger.info(f"GeminiClient initialization completed successfully. Current status: {client.account_status.name}")
        
    except Exception as e:
        logger.exception("A fatal error occurred during GeminiClient initialization. Aborting application startup.")
        raise e
    yield
    
    logger.info("Application shutdown: Starting GeminiClient.close().")
    await client.close()
    logger.info("GeminiClient session closed successfully.")

app = FastAPI(title="Gemini WebAPI OpenAI Wrapper", lifespan=lifespan)

# --- Request Logging Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    logger.info(f"Access received | Client IP: {client_host} | Method: {method} | Path: {path}")
    
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    logger.info(f"Access completed | Client IP: {client_host} | Method: {method} | Path: {path} | Status: {response.status_code} | Process time: {process_time:.2f}ms")
    return response

# --- OpenAI API Compatible Data Structures ---
class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None

# Helper to extract binary data from Base64 Data URL
def parse_image_data_url(data_url: str) -> bytes:
    match = re.match(r"data:image/(?P<ext>[^;]+);base64,(?P<data>.+)", data_url)
    if not match:
        logger.error("Invalid image data URL format detected.")
        raise HTTPException(status_code=400, detail="Invalid image data URL format.")
    data_str = match.group("data")
    return base64.b64decode(data_str)

# --- Endpoint Implementations ---

@app.get("/v1/models")
async def list_models():
    """Returns a list of models so that clients like Aider can enable vision capabilities (image recognition) etc."""
    logger.info("Processing internal logic for endpoint /v1/models...")
    return {
        "object": "list",
        "data": [
            {"id": "gemini-3-flash-thinking", "object": "model", "owned_by": "google"},
            {"id": "gemini-3-pro", "object": "model", "owned_by": "google"}
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(body: ChatCompletionRequest):
    logger.info(f"Endpoint /v1/chat/completions internal process started | Model: {body.model} | Stream: {body.stream} | Message count: {len(body.messages)}")
    
    if not body.messages:
        logger.warning("Request messages are empty.")
        raise HTTPException(status_code=400, detail="Messages cannot be empty.")
    
    prompt_text = ""
    uploaded_files = []
    temp_file_paths = []

    logger.info(f"Starting to traverse all messages (Count: {len(body.messages)}).")

    # Loop through all messages in conversation history to combine text and extract images
    for msg in body.messages:
        role = msg.role
        
        # Parse multimodal content (list format with text + images)
        if isinstance(msg.content, list):
            msg_text = ""
            for part in msg.content:
                part_type = part.get("type")
                if part_type == "text":
                    msg_text += part.get("text", "")
                elif part_type == "image_url":
                    image_url_obj = part.get("image_url", {})
                    url_data = image_url_obj.get("url", "")
                    
                    if url_data.startswith("data:image"):
                        try:
                            image_bytes = parse_image_data_url(url_data)
                            byte_size_kb = len(image_bytes) / 1024
                            
                            logger.info(f"Image parsed successfully | Sender role: {role} | Format: Base64 Data URL | Size: {byte_size_kb:.2f} KB")
                            
                            # Create a .png temporary file and write to disk to avoid extension loss issue in in-memory data
                            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                                tf.write(image_bytes)
                                temp_file_path = tf.name
                            
                            uploaded_files.append(temp_file_path)
                            temp_file_paths.append(temp_file_path)
                            logger.info(f"Saved image as a temporary file on disk: {temp_file_path}")
                        except Exception as e:
                            logger.error(f"An exception occurred during image parsing. Details: {e}")
                            raise HTTPException(status_code=400, detail=f"Failed to decode image: {str(e)}")
                    else:
                        logger.warning(f"Skipping unsupported image URL schema | Role: {role} | URL preview: {url_data[:120]}...")
            
            if msg_text:
                prompt_text += f"\n[{role}]: {msg_text}"
                
        # Parse standard text format (str)
        else:
            if msg.content:
                prompt_text += f"\n[{role}]: {msg.content}"

    prompt_text = prompt_text.strip()
    logger.info(f"Completed traversing all messages. Detected images: {len(uploaded_files)}")
    logger.debug(f"Parsed prompt text: {prompt_text[:100]}...")
    target_model = body.model

    # Streaming response handling
    if body.stream:
        logger.info("Starting streaming response mode.")
        async def stream_generator():
            try:
                chunk_count = 0
                async for chunk in client.generate_content_stream(prompt=prompt_text, files=uploaded_files if uploaded_files else None, model=target_model):
                    chunk_count += 1
                    
                    # Process Reasoning (thoughts) delta
                    if hasattr(chunk, 'thoughts_delta') and chunk.thoughts_delta:
                        reasoning_payload = {
                            "id": "chatcmpl-123", "object": "chat.completion.chunk", "created": int(time.time()), "model": target_model,
                            "choices": [{"index": 0, "delta": {"reasoning_content": chunk.thoughts_delta}, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(reasoning_payload)}\n\n"

                    # Process standard text delta
                    if hasattr(chunk, 'text_delta') and chunk.text_delta:
                        text_payload = {
                            "id": "chatcmpl-123", "object": "chat.completion.chunk", "created": int(time.time()), "model": target_model,
                            "choices": [{"index": 0, "delta": {"content": chunk.text_delta}, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(text_payload)}\n\n"
                
                logger.info(f"Streaming completed. Total chunks: {chunk_count}")
                
                # Send finish signal
                final_payload = {
                    "id": "chatcmpl-123", "object": "chat.completion.chunk", "created": int(time.time()), "model": target_model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(final_payload)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.exception("An error occurred during streaming generation.")
                error_payload = {"error": {"message": str(e), "type": "internal_error"}}
                yield f"data: {json.dumps(error_payload)}\n\n"
            finally:
                if temp_file_paths:
                    logger.info(f"Running cleanup process: Deleting {len(temp_file_paths)} temporary files.")
                    for path in temp_file_paths:
                        try:
                            if os.path.exists(path):
                                os.unlink(path)
                        except Exception as e:
                            logger.error(f"Failed to delete temporary file {path}: {e}")

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming (bulk) response handling
    else:
        logger.info("Starting non-streaming (bulk) response mode.")
        try:
            output = await client.generate_content(
                prompt=prompt_text,
                files=uploaded_files if uploaded_files else None,
                model=target_model
            )
            
            # Extract response text
            main_text = output.text_delta if hasattr(output, 'text_delta') else ""
            if not main_text and hasattr(output, 'candidates') and output.candidates:
                main_text = output.candidates[0].text

            # Extract reasoning process (thoughts)
            thoughts = ""
            if hasattr(output, 'thoughts') and output.thoughts:
                thoughts = output.thoughts
            elif hasattr(output, 'candidates') and output.candidates and hasattr(output.candidates[0], 'thoughts'):
                thoughts = output.candidates[0].thoughts

            logger.info("Successfully retrieved response from GeminiClient. Constructing response payload.")
            response_json = {
                "id": "chatcmpl-123", "object": "chat.completion", "created": int(time.time()), "model": target_model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": main_text, "reasoning_content": thoughts if thoughts else None},
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
            return response_json
        except Exception as e:
            logger.exception("An error occurred during non-streaming response processing.")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Ensure all temporary files are deleted to free disk resources upon synchronous processing completion
            if temp_file_paths:
                logger.info(f"Running cleanup process: Deleting {len(temp_file_paths)} temporary files.")
                for path in temp_file_paths:
                    try:
                        if os.path.exists(path):
                            os.unlink(path)
                    except Exception as e:
                        logger.error(f"Failed to delete temporary file {path}: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6969)
