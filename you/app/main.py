import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles

load_dotenv()
from . import engine            # noqa: E402
from .gemini_client import listen  # noqa: E402

app = FastAPI(title="Sakhi - voice guide to government schemes")
# Server is STATELESS on purpose: facts travel with each request, audio is never saved.


@app.get("/api/start")
def start(lang: str = "hi"):
    lang = engine.safe_lang(lang)
    key = engine.next_question({})
    return {"speech": [engine.say(lang, "greet"), engine.ask(lang, key)],
            "asked": key, "facts": {}, "card": None}


@app.post("/api/turn")
async def turn(lang: str = Form("hi"), asked: str = Form(...),
               facts: str = Form("{}"), audio: UploadFile = File(...)):
    lang = engine.safe_lang(lang)
    if asked not in engine.QUESTION_ORDER:
        asked = engine.QUESTION_ORDER[0]
    old = json.loads(facts)
    try:
        heard = listen(await audio.read(), engine.PHRASES[lang]["name"], asked)
        merged = engine.merge(old, heard.facts.model_dump())
        understood = merged.get(asked) is not None and not heard.wants_repeat
    except Exception:
        merged, understood = old, False

    if not understood:
        return {"speech": [engine.say(lang, "retry"), engine.ask(lang, asked)],
                "asked": asked, "facts": merged, "card": None}

    nxt = engine.next_question(merged)
    if nxt:
        return {"speech": [engine.ask(lang, nxt)], "asked": nxt, "facts": merged, "card": None}
    return engine.final(merged, lang)


app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "static", html=True), name="static")