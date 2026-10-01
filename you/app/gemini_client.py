"""Gemini is only the EARS: audio in -> structured facts out.
It never decides eligibility (that is engine.py), so it cannot hallucinate a scheme."""
import os
from google import genai
from google.genai import types
from .models import Heard

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


SYSTEM = """You are the ears of a voice assistant for rural Indian women who have never used the internet.
She speaks in LANG, maybe in a local dialect, with hesitation or background noise.
Extract ONLY what she clearly said. Never guess; if unclear, use null.
- A plain yes or no answers the question she was just asked.
- Numbers may be spoken as words (ek, do, teen, oru, rendu, moonu). 'No children' or 'this is my first' means living_children = 0.
- wants_repeat = true if she asks to repeat, or says she did not understand."""


def listen(audio_wav: bytes, lang_name: str, asked: str) -> Heard:
    resp = _get_client().models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),
            f"The question she was just asked is about: {asked}. Extract her answer.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM.replace("LANG", lang_name),
            response_mime_type="application/json",
            response_schema=Heard,
            temperature=0.0,
        ),
    )
    return resp.parsed