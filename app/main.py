import csv
import hashlib
import io
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v20.0")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class MetaCredentials(BaseModel):
    access_token: str = Field(..., min_length=20)
    ad_account_id: str = Field(..., description="Format: act_<id>")
    app_id: str | None = None
    app_secret: str | None = None


class AIGenerateRequest(BaseModel):
    objective: str
    audience_description: str
    offer: str
    tone: str = "professional"
    call_to_action: str = "Learn more"


app = FastAPI(title="MetaB2B", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


def normalize_and_validate_emails(raw_text: str) -> list[str]:
    candidates = re.split(r"[\n,;\t\s]+", raw_text)
    cleaned = []
    seen = set()

    for item in candidates:
        email = item.strip().lower()
        if not email:
            continue
        if EMAIL_RE.match(email) and email not in seen:
            seen.add(email)
            cleaned.append(email)

    return cleaned


def hash_emails_sha256(emails: list[str]) -> list[str]:
    return [hashlib.sha256(e.encode("utf-8")).hexdigest() for e in emails]


@app.get("/")
async def home() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/meta/validate")
async def validate_meta_credentials(payload: MetaCredentials) -> dict[str, Any]:
    url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/me"
    params = {"access_token": payload.access_token, "fields": "id,name"}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Meta credentials or token")

    data = response.json()
    return {
        "ok": True,
        "meta_user": data,
        "ad_account_id": payload.ad_account_id,
    }


@app.post("/api/meta/upload-audience")
async def upload_audience(
    access_token: str = Form(...),
    ad_account_id: str = Form(...),
    audience_name: str = Form(...),
    email_file: UploadFile = File(...),
) -> dict[str, Any]:
    if not ad_account_id.startswith("act_"):
        raise HTTPException(status_code=400, detail="ad_account_id must start with 'act_'")

    content = await email_file.read()
    text = content.decode("utf-8", errors="ignore")

    if email_file.filename and email_file.filename.endswith(".csv"):
        reader = csv.reader(io.StringIO(text))
        flattened = "\n".join(cell for row in reader for cell in row)
        emails = normalize_and_validate_emails(flattened)
    else:
        emails = normalize_and_validate_emails(text)

    if not emails:
        raise HTTPException(status_code=400, detail="No valid emails found in upload")

    hashed = hash_emails_sha256(emails)

    create_audience_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{ad_account_id}/customaudiences"
    create_payload = {
        "name": audience_name,
        "subtype": "CUSTOM",
        "customer_file_source": "USER_PROVIDED_ONLY",
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        create_resp = await client.post(create_audience_url, data=create_payload)
        if create_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Audience create failed: {create_resp.text}")

        audience_id = create_resp.json().get("id")
        add_users_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{audience_id}/users"
        add_payload = {
            "payload": {
                "schema": ["EMAIL_SHA256"],
                "data": [[h] for h in hashed],
            },
            "access_token": access_token,
        }
        add_resp = await client.post(add_users_url, json=add_payload)

    if add_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to add users: {add_resp.text}")

    return {
        "ok": True,
        "audience_id": audience_id,
        "accepted_email_count": len(emails),
        "meta_response": add_resp.json(),
    }


@app.post("/api/ai/generate-ad")
async def generate_ad(payload: AIGenerateRequest) -> dict[str, str]:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    prompt = (
        "You are a senior paid social copywriter. "
        "Create Meta ad copy from the user's request. "
        "Return JSON with keys: primary_text, headline, description, cta, image_prompt."
    )
    user_message = (
        f"Objective: {payload.objective}\n"
        f"Audience: {payload.audience_description}\n"
        f"Offer: {payload.offer}\n"
        f"Tone: {payload.tone}\n"
        f"CTA: {payload.call_to_action}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"AI generation failed: {response.text}")

    content = response.json()["choices"][0]["message"]["content"]
    return {"ok": True, "ad": content}
