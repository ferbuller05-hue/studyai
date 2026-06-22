import anthropic
import PyPDF2
import io
from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def extrair_texto_pdf(arquivo_bytes: bytes) -> str:
    texto = ""
    pdf = PyPDF2.PdfReader(io.BytesIO(arquivo_bytes))
    for pagina in pdf.pages:
        texto += pagina.extract_text() or ""
    return texto.strip()

def extrair_topicos(texto: str) -> list[str]:
    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": f"""Analise o texto abaixo de uma prova ou material de estudo.
Extraia os principais tópicos e assuntos abordados.
Retorne APENAS uma lista de tópicos, um por linha, sem numeração ou bullets.
Máximo 8 tópicos. Seja específico.

Texto:
{texto[:3000]}"""
            }
        ]
    )
    topicos_raw = resposta.content[0].text.strip()
    topicos = [t.strip() for t in topicos_raw.split("\n") if t.strip()]
    return topicos[:8]

def processar_pdf(arquivo_bytes: bytes) -> list[str]:
    texto = extrair_texto_pdf(arquivo_bytes)
    if not texto:
        return ["Não foi possível extrair texto do PDF"]
    return extrair_topicos(texto)
    