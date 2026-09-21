"""Authenticated local test API. Each request owns its MCP subprocess."""
import asyncio
import os
import secrets
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv
from core.chat import AgentLimitError
from core.ollama_service import ModelResponseError
from core.runtime import ROOT, open_chat

load_dotenv(ROOT / ".env")
bearer = HTTPBearer(auto_error=False)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=32000)
    allow_edits: bool = False


class ChatResponse(BaseModel):
    reply: str


def create_app(chat_factory=open_chat):
    @asynccontextmanager
    async def lifespan(app):
        token = os.getenv("SECURITYMCP_API_KEY", "")
        if len(token) < 32:
            raise RuntimeError("Run python configure.py to generate SECURITYMCP_API_KEY")
        app.state.api_key = token
        app.state.slots = asyncio.Semaphore(2)
        yield

    app = FastAPI(title="SecurityMCP Ollama API", version="0.2.0", lifespan=lifespan)

    async def authenticate(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
        supplied = credentials.credentials if credentials else ""
        if not secrets.compare_digest(supplied.encode(), app.state.api_key.encode()):
            raise HTTPException(401, "Invalid API token", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/health")
    async def health():
        # Liveness only: this deliberately does not claim Ollama is reachable.
        return {"status": "ok", "provider": "ollama",
                "model": os.getenv("OLLAMA_MODEL", "qwen3:8b")}

    @app.post("/v1/chat", response_model=ChatResponse, dependencies=[Depends(authenticate)])
    async def chat(request: ChatRequest):
        acquired = False
        try:
            await asyncio.wait_for(app.state.slots.acquire(), timeout=0.1)
            acquired = True
            # MCP cleanup must stay in the same task as context entry.
            async with asyncio.timeout(300):
                async with chat_factory(allow_edits=request.allow_edits) as agent:
                    return ChatResponse(reply=await agent.run(request.message))
        except httpx.ConnectError:
            raise HTTPException(503, "Cannot reach Ollama. Start Ollama and check OLLAMA_HOST.") from None
        except (TimeoutError, httpx.TimeoutException):
            raise HTTPException(504 if acquired else 429, "Request timed out" if acquired else "Server busy") from None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                detail = "Model or endpoint not found. Run ollama pull for OLLAMA_MODEL and check OLLAMA_HOST."
            else:
                detail = "Ollama rejected the request. Check that the selected model supports tools."
            raise HTTPException(502, detail) from None
        except ValueError:
            raise HTTPException(400, "Invalid command or document; check the request") from None
        except AgentLimitError:
            raise HTTPException(422, "Tool-call limit reached") from None
        except (httpx.HTTPError, ModelResponseError):
            raise HTTPException(502, "Ollama returned an invalid or incomplete response") from None
        except Exception:
            raise HTTPException(502, "MCP service failed") from None
        finally:
            if acquired:
                app.state.slots.release()

    return app


app = create_app()
