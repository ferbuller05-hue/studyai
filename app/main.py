import asyncio
import hashlib, secrets, json
from concurrent.futures import ThreadPoolExecutor
from datetime import date as dt_date
from fastapi import FastAPI, Request, UploadFile, File, Form, Header
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.extractor import (processar_arquivo, extrair_topicos_do_prompt,
                            diagnosticar_material, diagnosticar_material_imagem,
                            extrair_texto_pdf, extrair_texto_docx, extrair_texto_txt,
                            extrair_topicos_da_imagem, gerar_estrutura_trilha)
from app.youtube import buscar_videos_por_topicos, buscar_videos_trilha, buscar_e_rankear_topico
from app.chat import responder
from app.feedback import analisar_feedback
from app.progresso import gerar_analise_progresso
from app.config import PREMIUM_TOKENS, ADMIN_KEY, MP_LINK, WHATSAPP
from app.database import engine, Base, SessionLocal
from app.models.onboarding import OnboardingProfile
from app.routers import onboarding as onboarding_router
from app.cache import cache_size

# Thread pool para rodar funções bloqueantes (Anthropic SDK, YouTube)
# sem travar o event loop do FastAPI
_executor = ThreadPoolExecutor(max_workers=8)

# Cria tabelas no banco se não existirem (fallback para dev sem rodar alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="StudyAI", version="0.6.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(onboarding_router.router)


# ── HELPERS ──────────────────────────────────────────────────────────────
def is_premium(token: str) -> bool:
    return bool(token and token.strip() in PREMIUM_TOKENS)


# ── ROTAS PRINCIPAIS ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request,
                                                      "mp_link": MP_LINK,
                                                      "whatsapp": WHATSAPP})


async def _buscar_videos_paralelo(temas_prioritarios: list, temas_info: list) -> list:
    """
    Busca e rankeia vídeos para todos os tópicos em PARALELO usando ThreadPoolExecutor.

    ANTES: sequencial — 5 tópicos × (YouTube + Claude) = ~7s
    DEPOIS: paralelo  — todos os tópicos ao mesmo tempo = ~1.5s (limitado pelo mais lento)
    """
    if not temas_prioritarios:
        return []

    temas_map = {t["nome"]: t for t in temas_info}
    loop = asyncio.get_event_loop()

    async def _uma_busca(topico: str) -> list:
        info = temas_map.get(topico, {})
        nivel = info.get("nivel", "intermediário")
        return await loop.run_in_executor(
            _executor,
            lambda t=topico, n=nivel: buscar_e_rankear_topico(t, n)
        )

    resultados = await asyncio.gather(*[_uma_busca(t) for t in temas_prioritarios],
                                      return_exceptions=True)

    videos: list = []
    for r in resultados:
        if isinstance(r, list):
            videos.extend(r[:2])  # 2 melhores por tópico
    return videos


@app.post("/analisar", response_class=HTMLResponse)
async def analisar(request: Request, arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    extensao = arquivo.filename.lower().split('.')[-1] if '.' in arquivo.filename else ''

    FORMATOS_IMAGEM = {'jpg', 'jpeg', 'png', 'webp'}
    loop = asyncio.get_event_loop()

    if extensao == 'pdf' or 'pdf' in (arquivo.content_type or ''):
        texto = await loop.run_in_executor(_executor, extrair_texto_pdf, conteudo)
        diagnostico = await loop.run_in_executor(_executor, diagnosticar_material, texto) if texto.strip() else {}

    elif extensao == 'docx':
        texto = await loop.run_in_executor(_executor, extrair_texto_docx, conteudo)
        diagnostico = await loop.run_in_executor(_executor, diagnosticar_material, texto) if texto.strip() else {}

    elif extensao == 'txt':
        texto = await loop.run_in_executor(_executor, extrair_texto_txt, conteudo)
        diagnostico = await loop.run_in_executor(_executor, diagnosticar_material, texto) if texto.strip() else {}

    elif extensao in FORMATOS_IMAGEM or 'image' in (arquivo.content_type or ''):
        mime = 'image/jpeg'
        if extensao == 'png':  mime = 'image/png'
        elif extensao == 'webp': mime = 'image/webp'
        diagnostico = await loop.run_in_executor(
            _executor, lambda: diagnosticar_material_imagem(conteudo, mime)
        )

    else:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "erro_upload": f"Formato '.{extensao}' não suportado. Use PDF, DOCX, TXT, JPG ou PNG.",
            "mp_link": MP_LINK, "whatsapp": WHATSAPP
        })

    # Máx 3 tópicos (era 5) — reduz de 10 para 6 chamadas externas
    temas_info = diagnostico.get("temas", [])
    temas_prioritarios = [
        t["nome"] for t in temas_info if t.get("prioridade") in ["alta", "média"]
    ][:3] or [t["nome"] for t in temas_info][:3]

    # PARALELO: todas as buscas de vídeo ao mesmo tempo
    videos = await _buscar_videos_paralelo(temas_prioritarios, temas_info)

    return templates.TemplateResponse("index.html", {
        "request": request, "diagnostico": diagnostico,
        "videos": videos, "modo": "arquivo",
        "mp_link": MP_LINK, "whatsapp": WHATSAPP
    })


@app.post("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, prompt: str = Form(...)):
    loop = asyncio.get_event_loop()
    diagnostico = await loop.run_in_executor(_executor, diagnosticar_material, prompt)

    temas_info = diagnostico.get("temas", [])
    temas_prioritarios = [
        t["nome"] for t in temas_info if t.get("prioridade") in ["alta", "média"]
    ][:3] or [t["nome"] for t in temas_info][:3]

    videos = await _buscar_videos_paralelo(temas_prioritarios, temas_info)

    return templates.TemplateResponse("index.html", {
        "request": request, "diagnostico": diagnostico,
        "videos": videos, "prompt": prompt, "modo": "texto",
        "mp_link": MP_LINK, "whatsapp": WHATSAPP
    })


@app.post("/trilha", response_class=HTMLResponse)
async def trilha(request: Request, temas_json: str = Form(...),
                 token: str = Form(default=""),
                 perfil_json: str = Form(default="")):
    # ── PAYWALL ──
    if not is_premium(token):
        return templates.TemplateResponse("upgrade.html", {
            "request": request, "mp_link": MP_LINK, "whatsapp": WHATSAPP,
            "motivo": "A Trilha de Estudo é um recurso Premium."
        })

    temas = json.loads(temas_json)
    perfil = json.loads(perfil_json) if perfil_json else None
    estrutura = gerar_estrutura_trilha(temas, perfil=perfil)
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
    return {"status": "ok", "cache_entries": cache_size()}


@app.get("/ping")
async def ping():
    """
    Endpoint ultra-leve para keep-alive externo.
    Configure um cron gratuito (cron-job.org) para chamar este endpoint
    a cada 10 minutos e evitar o cold start do Render free tier.
    """
    return "pong"


# ── DIAGNÓSTICO PREMIUM ───────────────────────────────────────────────────────

@app.get("/diagnostico-premium", response_class=HTMLResponse)
async def diagnostico_premium_page(request: Request):
    """Página de entrada do diagnóstico premium — mostra formulário."""
    return templates.TemplateResponse("diagnostico_premium.html", {
        "request": request, "mp_link": MP_LINK, "whatsapp": WHATSAPP,
        "diagnostico": None,
    })


@app.post("/diagnostico-premium", response_class=HTMLResponse)
async def diagnostico_premium_run(
    request: Request,
    arquivo: UploadFile = File(None),
    prompt: str = Form(default=""),
    token: str = Form(default=""),
    session_id: str = Form(default=""),
):
    if not is_premium(token):
        return templates.TemplateResponse("upgrade.html", {
            "request": request, "mp_link": MP_LINK, "whatsapp": WHATSAPP,
            "motivo": "Diagnóstico Premium é exclusivo para assinantes.",
        })

    # ── Perfil de onboarding ──────────────────────────────────────────────
    horas_por_dia = 2.0
    dias_restantes = None
    horas_totais = None

    if session_id:
        db = SessionLocal()
        try:
            perfil = db.query(OnboardingProfile).filter(
                OnboardingProfile.session_id == session_id
            ).first()
            if perfil:
                horas_por_dia = perfil.horas_por_dia
                if perfil.data_prova:
                    dias_restantes = max(0, (perfil.data_prova - dt_date.today()).days)
                    horas_totais = round(dias_restantes * horas_por_dia)
        finally:
            db.close()

    # ── Diagnóstico ───────────────────────────────────────────────────────
    diagnostico = {}
    if arquivo and arquivo.filename:
        conteudo = await arquivo.read()
        extensao = arquivo.filename.lower().split(".")[-1] if "." in arquivo.filename else ""
        if extensao == "pdf" or "pdf" in (arquivo.content_type or ""):
            texto = extrair_texto_pdf(conteudo)
            diagnostico = diagnosticar_material(texto) if texto.strip() else {}
        else:
            mime = "image/jpeg"
            if extensao == "png": mime = "image/png"
            elif extensao == "webp": mime = "image/webp"
            diagnostico = diagnosticar_material_imagem(conteudo, mime)
    elif prompt:
        diagnostico = diagnosticar_material(prompt)

    # ── Métricas premium ──────────────────────────────────────────────────
    temas = diagnostico.get("temas", [])
    temas_alta  = [t for t in temas if t.get("prioridade") == "alta"]
    temas_media = [t for t in temas if t.get("prioridade") == "média"]
    temas_baixa = [t for t in temas if t.get("prioridade") not in ("alta", "média")]

    if dias_restantes and dias_restantes > 0 and horas_totais:
        horas_nec = len(temas_alta) * 3 + len(temas_media) * 2 + len(temas_baixa) * 1
        cobertura = min(1.0, horas_totais / max(horas_nec, 1))
        chance = int(min(95, max(30, 35 + cobertura * 55)))
    else:
        chance = 58

    recomendacao = temas_alta[0] if temas_alta else (temas_media[0] if temas_media else None)

    temas_cobre  = min(int(horas_totais / 2.5), len(temas)) if horas_totais else 0
    semanas_disponiveis = min(max(1, dias_restantes // 7), 8) if dias_restantes else 0

    return templates.TemplateResponse("diagnostico_premium.html", {
        "request":               request,
        "diagnostico":           diagnostico,
        "temas_alta":            temas_alta,
        "temas_media":           temas_media,
        "temas_baixa":           temas_baixa,
        "chance":                chance,
        "horas_por_dia":         horas_por_dia,
        "dias_restantes":        dias_restantes,
        "horas_totais":          horas_totais,
        "recomendacao":          recomendacao,
        "temas_cobre":           temas_cobre,
        "semanas_disponiveis":   semanas_disponiveis,
        "mp_link":               MP_LINK,
        "whatsapp":              WHATSAPP,
    })
