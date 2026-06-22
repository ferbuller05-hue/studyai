import hashlib, secrets, json
from fastapi import FastAPI, Request, UploadFile, File, Form, Header
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.extractor import (processar_arquivo, extrair_topicos_do_prompt,
                            diagnosticar_material, diagnosticar_material_imagem,
                            extrair_texto_pdf, extrair_topicos_da_imagem,
                            gerar_estrutura_trilha)
from app.youtube import buscar_videos_por_topicos, buscar_videos_trilha
from app.chat import responder
from app.feedback import analisar_feedback
from app.progresso import gerar_analise_progresso
from app.config import PREMIUM_TOKENS, ADMIN_KEY, MP_LINK, WHATSAPP

app = FastAPI(title="StudyAI", version="0.5.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ── HELPERS ──────────────────────────────────────────────────────────────
def is_premium(token: str) -> bool:
    return bool(token and token.strip() in PREMIUM_TOKENS)


# ── ROTAS PRINCIPAIS ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request,
                                                      "mp_link": MP_LINK,
                                                      "whatsapp": WHATSAPP})


@app.post("/analisar", response_class=HTMLResponse)
async def analisar(request: Request, arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    extensao = arquivo.filename.lower().split('.')[-1] if '.' in arquivo.filename else ''

    if extensao == 'pdf' or 'pdf' in (arquivo.content_type or ''):
        texto = extrair_texto_pdf(conteudo)
        diagnostico = diagnosticar_material(texto) if texto.strip() else {}
    else:
        mime = 'image/jpeg'
        if extensao == 'png': mime = 'image/png'
        elif extensao == 'webp': mime = 'image/webp'
        diagnostico = diagnosticar_material_imagem(conteudo, mime)

    temas_prioritarios = [
        t["nome"] for t in diagnostico.get("temas", [])
        if t.get("prioridade") in ["alta", "média"]
    ][:5] or [t["nome"] for t in diagnostico.get("temas", [])][:5]

    videos = buscar_videos_por_topicos(temas_prioritarios,
                                       temas_info=diagnostico.get("temas", [])) if temas_prioritarios else []

    return templates.TemplateResponse("index.html", {
        "request": request, "diagnostico": diagnostico,
        "videos": videos, "modo": "arquivo",
        "mp_link": MP_LINK, "whatsapp": WHATSAPP
    })


@app.post("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, prompt: str = Form(...)):
    diagnostico = diagnosticar_material(prompt)

    temas_prioritarios = [
        t["nome"] for t in diagnostico.get("temas", [])
        if t.get("prioridade") in ["alta", "média"]
    ][:5] or [t["nome"] for t in diagnostico.get("temas", [])][:5]

    videos = buscar_videos_por_topicos(temas_prioritarios,
                                       temas_info=diagnostico.get("temas", [])) if temas_prioritarios else []

    return templates.TemplateResponse("index.html", {
        "request": request, "diagnostico": diagnostico,
        "videos": videos, "prompt": prompt, "modo": "texto",
        "mp_link": MP_LINK, "whatsapp": WHATSAPP
    })


@app.post("/trilha", response_class=HTMLResponse)
async def trilha(request: Request, temas_json: str = Form(...),
                 token: str = Form(default="")):
    # ── PAYWALL ──
    if not is_premium(token):
        return templates.TemplateResponse("upgrade.html", {
            "request": request, "mp_link": MP_LINK, "whatsapp": WHATSAPP,
            "motivo": "A Trilha de Estudo é um recurso Premium."
        })

    temas = json.loads(temas_json)
    estrutura = gerar_estrutura_trilha(temas)
    videos_trilha = buscar_videos_trilha(estrutura.get("etapas", []))

    return templates.TemplateResponse("trilha.html", {
        "request": request, "trilha": estrutura, "videos": videos_trilha,
    })


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    resposta = responder(data.get("mensagem", ""),
                         data.get("historico", []),
                         data.get("topicos", []))
    return JSONResponse({"resposta": resposta})


@app.post("/feedback")
async def feedback(request: Request):
    data = await request.json()
    resultado = analisar_feedback(
        tema=data.get("tema", ""),
        video_titulo=data.get("video_titulo", ""),
        entendimento=int(data.get("entendimento", 70)),
        dificuldade=data.get("dificuldade", "médio"),
        comentario=data.get("comentario", ""),
        dominio_atual=int(data.get("dominio_atual", 0)),
        historico_erros=data.get("historico_erros", [])
    )
    return JSONResponse(resultado)


@app.get("/progresso", response_class=HTMLResponse)
async def pagina_progresso(request: Request):
    return templates.TemplateResponse("progresso.html", {"request": request})


@app.post("/progresso-analise")
async def progresso_analise(request: Request):
    data = await request.json()
    analise = gerar_analise_progresso(
        data.get("perfil", {}),
        int(data.get("streak", 0)),
        int(data.get("dias_sem_estudo", 0))
    )
    return JSONResponse(analise)


# ── PAYWALL: validar token ────────────────────────────────────────────────
@app.post("/validar-token")
async def validar_token(request: Request):
    data = await request.json()
    token = data.get("token", "").strip().upper()
    if is_premium(token):
        return JSONResponse({"valido": True})
    return JSONResponse({"valido": False}, status_code=200)


# ── ADMIN: gerar token (protegido por ADMIN_KEY) ─────────────────────────
@app.get("/admin/gerar-token")
async def gerar_token(request: Request, key: str = ""):
    if not ADMIN_KEY or key != ADMIN_KEY:
        return JSONResponse({"erro": "Não autorizado"}, status_code=403)
    # Gera token no formato SAI-XXXX-XXXX-XXXX
    parte = lambda: secrets.token_hex(2).upper()
    novo_token = f"SAI-{parte()}-{parte()}-{parte()}"
    return JSONResponse({
        "token": novo_token,
        "instrucao": f"Adicione '{novo_token}' à variável PREMIUM_TOKENS no Render (separado por vírgula) e faça redeploy."
    })


@app.get("/upgrade", response_class=HTMLResponse)
async def upgrade(request: Request):
    return templates.TemplateResponse("upgrade.html", {
        "request": request, "mp_link": MP_LINK, "whatsapp": WHATSAPP, "motivo": ""
    })


@app.get("/health")
async def health():
    return {"status": "ok"}
