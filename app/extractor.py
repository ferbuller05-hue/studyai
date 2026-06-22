import anthropic
import PyPDF2
import io
import base64
from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def extrair_texto_pdf(arquivo_bytes: bytes) -> str:
    texto = ""
    pdf = PyPDF2.PdfReader(io.BytesIO(arquivo_bytes))
    for pagina in pdf.pages:
        texto += pagina.extract_text() or ""
    return texto.strip()


def extrair_topicos_do_texto(texto: str) -> list[str]:
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


def extrair_topicos_da_imagem(arquivo_bytes: bytes, tipo_mime: str) -> list[str]:
    imagem_b64 = base64.standard_b64encode(arquivo_bytes).decode("utf-8")

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": tipo_mime,
                            "data": imagem_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Analise esta imagem de uma prova, caderno ou material de estudo.
Extraia os principais tópicos e assuntos abordados.
Retorne APENAS uma lista de tópicos, um por linha, sem numeração ou bullets.
Máximo 8 tópicos. Seja específico."""
                    }
                ],
            }
        ],
    )
    topicos_raw = resposta.content[0].text.strip()
    topicos = [t.strip() for t in topicos_raw.split("\n") if t.strip()]
    return topicos[:8]


def extrair_topicos_do_prompt(prompt: str) -> list[str]:
    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": f"""O estudante escreveu: "{prompt}"

Extraia os tópicos de estudo que ele precisa aprender.
Retorne APENAS uma lista de tópicos, um por linha, sem numeração ou bullets.
Máximo 6 tópicos. Seja específico e técnico."""
            }
        ]
    )
    topicos_raw = resposta.content[0].text.strip()
    topicos = [t.strip() for t in topicos_raw.split("\n") if t.strip()]
    return topicos[:6]


def processar_arquivo(arquivo_bytes: bytes, nome_arquivo: str, tipo_mime: str) -> list[str]:
    extensao = nome_arquivo.lower().split('.')[-1] if '.' in nome_arquivo else ''

    if extensao == 'pdf' or 'pdf' in tipo_mime:
        texto = extrair_texto_pdf(arquivo_bytes)
        if not texto:
            return ["Não foi possível extrair texto do PDF"]
        return extrair_topicos_do_texto(texto)

    elif extensao in ['jpg', 'jpeg', 'png', 'webp'] or 'image' in tipo_mime:
        if extensao in ['jpg', 'jpeg'] or 'jpeg' in tipo_mime:
            mime = 'image/jpeg'
        elif extensao == 'png' or 'png' in tipo_mime:
            mime = 'image/png'
        elif extensao == 'webp' or 'webp' in tipo_mime:
            mime = 'image/webp'
        else:
            mime = 'image/jpeg'
        return extrair_topicos_da_imagem(arquivo_bytes, mime)

    else:
        return ["Formato não suportado. Envie um PDF ou imagem (JPG, PNG)."]
