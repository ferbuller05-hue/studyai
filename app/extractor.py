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


def diagnosticar_material_imagem(arquivo_bytes: bytes, tipo_mime: str) -> dict:
    """Diagnóstico direto de imagem usando Claude Vision."""
    import json
    imagem_b64 = base64.standard_b64encode(arquivo_bytes).decode("utf-8")

    prompt_json = """{
  "temas": [{"nome": "...", "frequencia": 35, "nivel": "básico|intermediário|avançado", "prioridade": "alta|média|baixa"}],
  "ordem_recomendada": ["tema1", "tema2"],
  "dependencias": ["Para estudar X, precisa entender Y primeiro"],
  "resumo": "Uma frase resumindo o foco do material"
}"""

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1500,
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
                        "text": f"""Você é um especialista em análise educacional.
Analise esta imagem de um material de estudo (prova, caderno, lista, resumo).
Retorne APENAS um JSON válido neste formato:
{prompt_json}

Regras:
- Máximo 8 temas
- frequencia deve somar 100 entre todos os temas
- Ordene por prioridade (alta primeiro)
- Retorne APENAS o JSON, sem texto adicional"""
                    }
                ],
            }
        ],
    )
    try:
        texto = resposta.content[0].text.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        return json.loads(texto.strip())
    except Exception:
        return {"temas": [], "ordem_recomendada": [], "dependencias": [], "resumo": ""}


def diagnosticar_material(conteudo: str) -> dict:
    """
    Analisa profundamente o material e retorna um diagnóstico completo.
    conteudo pode ser texto extraído de PDF, imagem, ou prompt do usuário.
    """
    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": f"""Você é um especialista em análise educacional.
Analise o material abaixo e retorne um diagnóstico estruturado em JSON.

Material:
{conteudo[:4000]}

Retorne APENAS um JSON válido neste formato exato:
{{
  "temas": [
    {{
      "nome": "Nome do tema",
      "frequencia": 35,
      "nivel": "básico|intermediário|avançado",
      "prioridade": "alta|média|baixa"
    }}
  ],
  "ordem_recomendada": ["tema1", "tema2", "tema3"],
  "dependencias": ["Para estudar X, precisa entender Y primeiro"],
  "resumo": "Uma frase resumindo o foco principal do material"
}}

Regras:
- Máximo 8 temas
- frequencia deve somar 100 entre todos os temas
- Ordene os temas por prioridade (alta primeiro)
- Retorne APENAS o JSON, sem texto adicional"""
            }
        ]
    )

    import json
    try:
        texto = resposta.content[0].text.strip()
        # Remove possível markdown
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        return json.loads(texto.strip())
    except Exception:
        # Fallback simples se o JSON falhar
        return {
            "temas": [],
            "ordem_recomendada": [],
            "dependencias": [],
            "resumo": ""
        }


def gerar_estrutura_trilha(temas: list) -> dict:
    """Gera a trilha de aprendizado estruturada a partir dos temas do diagnóstico."""
    import json
    temas_str = json.dumps(temas, ensure_ascii=False, indent=2)

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Você é um especialista em educação. Crie uma trilha de aprendizado personalizada.

Temas identificados no diagnóstico:
{temas_str}

Retorne APENAS um JSON válido neste formato:
{{
  "etapas": [
    {{
      "ordem": 1,
      "tema": "Nome do tema",
      "objetivo": "O que o aluno vai conseguir fazer após estudar isso",
      "prerequisito": "Nome do tema anterior necessário, ou null",
      "tempo_estimado": "2h",
      "sessoes": [
        {{"tipo": "introducao", "descricao": "Como e o que estudar nessa etapa", "duracao": "30min"}},
        {{"tipo": "aprofundamento", "descricao": "O que aprofundar e como", "duracao": "40min"}},
        {{"tipo": "exercicios", "descricao": "Tipo de exercícios a praticar", "duracao": "30min"}},
        {{"tipo": "revisao", "descricao": "Como revisar e fixar o conteúdo", "duracao": "20min"}}
      ]
    }}
  ],
  "cronograma": [
    {{"dia": 1, "temas": ["tema1"], "carga": "2h"}},
    {{"dia": 2, "temas": ["tema2", "tema3"], "carga": "1h30min"}}
  ],
  "tempo_total": "X horas"
}}

Regras:
- Máximo 5 etapas (use apenas os temas de maior prioridade)
- Ordem lógica respeitando pré-requisitos
- Cronograma realista (1-2 temas por dia, máximo 3h por dia)
- Retorne APENAS o JSON, sem texto adicional"""
        }]
    )

    try:
        texto = resposta.content[0].text.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        return json.loads(texto.strip())
    except Exception:
        return {"etapas": [], "cronograma": [], "tempo_total": ""}


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
