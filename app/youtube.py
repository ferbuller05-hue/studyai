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
    if not videos:
        return []

    lista = "\n".join([f"{i+1}. {v['titulo']} - {v['canal']}" 
                       for i, v in enumerate(videos)])

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"""Dado o tópico "{topico}", qual desses vídeos é mais didático e relevante para estudar?
Responda APENAS com o número do melhor vídeo (1-{len(videos)}).

{lista}"""
        }]
    )

    try:
        melhor = int(resposta.content[0].text.strip()) - 1
        return [videos[melhor]] + [v for i, v in enumerate(videos) if i != melhor]
    except:
        return videos

def buscar_videos_por_topicos(topicos: list[str]) -> list[dict]:
    todos_videos = []
    for topico in topicos[:5]:
        videos = buscar_videos(topico)
        rankeados = rankear_videos(topico, videos)
        if rankeados:
            todos_videos.append(rankeados[0])
    return todos_videos