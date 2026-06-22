from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.extractor import processar_arquivo, extrair_topicos_do_prompt, diagnosticar_material, diagnosticar_material_imagem, extrair_texto_pdf, extrair_topicos_da_imagem, gerar_estrutura_trilha
from app.youtube import buscar_videos_por_topicos, buscar_videos_trilha
from app.chat import responder
import base64

app = FastAPI(title="StudyAI", version="0.4.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analisar", response_class=HTMLResponse)
async def analisar(request: Request, arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    extensao = arquivo.filename.lower().split('.')[-1] if '.' in arquivo.filename else ''

    # Extrai e diagnostica
    if extensao == 'pdf' or 'pdf' in (arquivo.content_type or ''):
        texto = extrair_texto_pdf(conteudo)
        diagnostico = diagnosticar_material(texto) if texto.strip() else {}
    else:
        mime = 'image/jpeg'
        if extensao == 'png': mime = 'image/png'
        elif extensao == 'webp': mime = 'image/webp'
        diagnostico = diagnosticar_material_imagem(conteudo, mime)

    # Busca vídeos pelos temas de alta prioridade
    temas_prioritarios = [
        t["nome"] for t in diagnostico.get("temas", [])
        if t.get("prioridade") in ["alta", "média"]
    ][:5]

    if not temas_prioritarios:
        temas_prioritarios = [t["nome"] for t in diagnostico.get("temas", [])][:5]

    videos = buscar_videos_por_topicos(temas_prioritarios, temas_info=diagnostico.get("temas", [])) if temas_prioritarios else []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "diagnostico": diagnostico,
        "videos": videos,
        "modo": "arquivo"
    })


@app.post("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, prompt: str = Form(...)):
    diagnostico = diagnosticar_material(prompt)

    temas_prioritarios = [
        t["nome"] for t in diagnostico.get("temas", [])
        if t.get("prioridade") in ["alta", "média"]
    ][:5]

    if not temas_prioritarios:
        temas_prioritarios = [t["nome"] for t in diagnostico.get("temas", [])][:5]

    videos = buscar_videos_por_topicos(temas_prioritarios, temas_info=diagnostico.get("temas", [])) if temas_prioritarios else []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "diagnostico": diagnostico,
        "videos": videos,
        "prompt": prompt,
        "modo": "texto"
    })


@app.post("/trilha", response_class=HTMLResponse)
async def trilha(request: Request, temas_json: str = Form(...)):
    import json
    temas = json.loads(temas_json)

    # Gera estrutura da trilha com Claude
    estrutura = gerar_estrutura_trilha(temas)

    # Busca vídeos específicos por etapa e tipo
    videos_trilha = buscar_videos_trilha(estrutura.get("etapas", []))

    return templates.TemplateResponse("trilha.html", {
        "request": request,
        "trilha": estrutura,
        "videos": videos_trilha,
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
