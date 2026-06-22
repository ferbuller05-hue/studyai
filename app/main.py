from fastapi import FastAPI, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.extractor import processar_arquivo
from app.youtube import buscar_videos_por_topicos

app = FastAPI(title="StudyAI", version="0.1.0")

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
        "videos": videos
    })

@app.get("/health")
async def health():
    return {"status": "ok"}
