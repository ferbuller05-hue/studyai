from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.extractor import processar_arquivo, extrair_topicos_do_prompt
from app.youtube import buscar_videos_por_topicos
from app.chat import responder
import json

app = FastAPI(title="StudyAI", version="0.3.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analisar", response_class=HTMLResponse)
async def analisar(request: Request, arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    topicos = processar_arquivo(conteudo, arquivo.filename, arquivo.content_type or "")
    videos = buscar_videos_por_topicos(topicos)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "topicos": topicos,
        "videos": videos,
        "modo": "arquivo"
    })


@app.post("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, prompt: str = Form(...)):
    topicos = extrair_topicos_do_prompt(prompt)
    videos = buscar_videos_por_topicos(topicos)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "topicos": topicos,
        "videos": videos,
        "prompt": prompt,
        "modo": "texto"
    })


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    mensagem = data.get("mensagem", "")
    historico = data.get("historico", [])
    topicos = data.get("topicos", [])

    resposta = responder(mensagem, historico, topicos)
    return JSONResponse({"resposta": resposta})


@app.get("/health")
async def health():
    return {"status": "ok"}
