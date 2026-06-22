from googleapiclient.discovery import build
from anthropic import Anthropic
from app.config import YOUTUBE_API_KEY, ANTHROPIC_API_KEY

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
client = Anthropic(api_key=ANTHROPIC_API_KEY)

def buscar_videos(topico: str) -> list[dict]:
    resultado = youtube.search().list(
        q=topico + " aula explicação",
        part="snippet",
        maxResults=5,
        type="video",
        relevanceLanguage="pt",
        videoDuration="medium"
    ).execute()

    videos = []
    for item in resultado.get("items", []):
        videos.append({
            "titulo": item["snippet"]["title"],
            "canal": item["snippet"]["channelTitle"],
            "video_id": item["id"]["videoId"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "topico": topico
        })
    return videos

def rankear_videos(topico: str, videos: list[dict]) -> list[dict]:
    """Ranking simples — fallback interno."""
    if not videos:
        return []
    lista = "\n".join([f"{i+1}. {v['titulo']} - {v['canal']}" for i, v in enumerate(videos)])
    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=10,
        messages=[{"role": "user", "content": f'Qual vídeo é mais didático para "{topico}"? Responda só o número.\n{lista}'}]
    )
    try:
        melhor = int(resposta.content[0].text.strip()) - 1
        return [videos[melhor]] + [v for i, v in enumerate(videos) if i != melhor]
    except:
        return videos


def rankear_videos_inteligente(topico: str, videos: list[dict], nivel: str = "intermediário", objetivo: str = "") -> list[dict]:
    """
    Ranking avançado: score 0–100, motivo, nível, tipo e cobertura para cada vídeo.
    Retorna os 3 melhores com metadados completos.
    """
    import json as _json
    if not videos:
        return []

    lista = "\n".join([
        f"{i+1}. Título: {v['titulo']} | Canal: {v['canal']}"
        for i, v in enumerate(videos)
    ])
    objetivo_str = f"\nObjetivo: {objetivo}" if objetivo else ""

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=900,
        messages=[{
            "role": "user",
            "content": f"""Você é especialista em recomendação educacional.

Tema: {topico}
Nível do aluno: {nivel}{objetivo_str}

Vídeos disponíveis:
{lista}

Analise e retorne APENAS um JSON com os 3 melhores vídeos rankeados:
[
  {{
    "numero": 2,
    "score": 87,
    "motivo": "Explica regra da cadeia com exemplos visuais, perfeito para quem está vendo pela primeira vez",
    "nivel_video": "intermediário",
    "tipo": "Conceito",
    "cobertura": "Derivadas básicas, regra da cadeia, derivada de funções compostas",
    "tempo_util": "18min",
    "timestamp": "2:30"
  }}
]

Critérios de score (0-100): aderência ao tema, qualidade didática, nível adequado, profundidade.
Tipos: Conceito | Exercício | Revisão
timestamp = minuto:segundo onde começa o conteúdo principal (pule intros longas).
tempo_util = tempo real necessário para assistir o que importa.
Retorne APENAS o JSON."""
        }]
    )

    try:
        texto = resposta.content[0].text.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        rankings = _json.loads(texto.strip())

        resultado = []
        for r in rankings:
            idx = r.get("numero", 1) - 1
            if 0 <= idx < len(videos):
                video = videos[idx].copy()
                video["score"] = r.get("score", 0)
                video["motivo"] = r.get("motivo", "")
                video["nivel_video"] = r.get("nivel_video", "")
                video["tipo_video"] = r.get("tipo", "")
                video["cobertura"] = r.get("cobertura", "")
                video["tempo_util"] = r.get("tempo_util", "")
                video["timestamp"] = r.get("timestamp", "")
                resultado.append(video)
        return resultado if resultado else videos[:3]
    except Exception:
        return videos[:3]

def buscar_videos_etapa(topico: str, tipo: str, nivel: str = "intermediário") -> dict | None:
    """Busca o melhor vídeo para uma etapa específica usando ranking inteligente."""
    queries = {
        "introducao": f"{topico} introdução explicação para iniciantes",
        "aprofundamento": f"{topico} aula completa aprofundamento",
        "exercicios": f"{topico} exercícios resolvidos lista",
        "revisao": f"{topico} revisão resumo rápido"
    }
    objetivo_map = {
        "introducao": "entender o conceito básico",
        "aprofundamento": "aprofundar o conhecimento",
        "exercicios": "praticar com exercícios resolvidos",
        "revisao": "revisar e fixar o conteúdo"
    }
    query = queries.get(tipo, f"{topico} aula")
    objetivo = objetivo_map.get(tipo, "")
    videos = buscar_videos(query)
    rankeados = rankear_videos_inteligente(topico, videos, nivel=nivel, objetivo=objetivo)
    if rankeados:
        rankeados[0]["tipo_sessao"] = tipo
    return rankeados[0] if rankeados else None


def buscar_videos_trilha(etapas: list) -> dict:
    """Retorna dict: tema → tipo → video com score inteligente. Máximo 4 temas."""
    resultado = {}
    for etapa in etapas[:4]:
        tema = etapa["tema"]
        nivel = etapa.get("nivel", "intermediário")
        resultado[tema] = {}
        for sessao in etapa.get("sessoes", []):
            tipo = sessao["tipo"]
            video = buscar_videos_etapa(tema, tipo, nivel=nivel)
            if video:
                resultado[tema][tipo] = video
    return resultado


def buscar_videos_por_topicos(topicos: list[str], temas_info: list = None) -> list[dict]:
    """Busca e rankeia vídeos com score inteligente. temas_info é a lista do diagnóstico."""
    todos_videos = []
    temas_map = {t["nome"]: t for t in (temas_info or [])}

    for topico in topicos[:5]:
        info = temas_map.get(topico, {})
        nivel = info.get("nivel", "intermediário")
        videos = buscar_videos(topico)
        rankeados = rankear_videos_inteligente(topico, videos, nivel=nivel)
        todos_videos.extend(rankeados[:2])  # 2 melhores por tópico
    return todos_videos