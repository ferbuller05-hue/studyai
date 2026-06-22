import anthropic
import json
from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def analisar_feedback(
    tema: str,
    video_titulo: str,
    entendimento: int,       # 0–100
    dificuldade: str,        # "fácil" | "médio" | "difícil"
    comentario: str,
    dominio_atual: int,      # 0–100, domínio anterior do tema
    historico_erros: list    # padrões de erro já registrados
) -> dict:
    """
    Analisa o feedback do aluno e retorna:
    - novo domínio (0–100)
    - próximo passo recomendado
    - padrões detectados
    - ajuste na trilha
    """

    historico_str = ", ".join(historico_erros) if historico_erros else "nenhum registrado"

    # Calcula velocidade de aprendizado com base no histórico
    velocidade = "média"
    if len(historico_erros) == 0 and dominio_atual == 0:
        velocidade = "indefinida"
    elif entendimento > 80 and dominio_atual < 50:
        velocidade = "rápida"
    elif entendimento < 60:
        velocidade = "lenta"

    # Calcula próxima revisão por repetição espaçada
    from datetime import datetime, timedelta
    hoje = datetime.now()
    if dominio_atual < 50:
        dias_revisao = 1
    elif dominio_atual < 70:
        dias_revisao = 3
    elif dominio_atual < 85:
        dias_revisao = 7
    else:
        dias_revisao = 14
    proxima_revisao = (hoje + timedelta(days=dias_revisao)).strftime("%Y-%m-%d")

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""Você é responsável por aprender com o progresso do aluno.

Dados da sessão:
- Tema: {tema}
- Vídeo assistido: {video_titulo}
- Nível de entendimento declarado: {entendimento}/100
- Dificuldade percebida: {dificuldade}
- Comentário do aluno: "{comentario or 'Nenhum'}"
- Domínio atual no tema: {dominio_atual}%
- Padrões de erro anteriores: {historico_str}

Regras de progressão:
- Entendimento < 60% → reduzir domínio em 5, recomendar conteúdo mais básico
- Entendimento 60–80% → manter ou aumentar 5, recomendar reforço
- Entendimento > 80% → aumentar 15, avançar para próximo nível

Retorne APENAS um JSON válido:
{{
  "novo_dominio": 65,
  "funcionou": "O que o aluno conseguiu assimilar",
  "nao_funcionou": "Onde teve dificuldade",
  "padroes": ["padrão detectado 1", "padrão detectado 2"],
  "proximo_passo": "O que estudar a seguir",
  "ajuste_trilha": "Como ajustar a trilha de estudos",
  "nivel_recomendado": "básico | intermediário | avançado",
  "mensagem_aluno": "Frase motivacional e direta para o aluno (máx 1 frase)"
}}

Retorne APENAS o JSON."""
        }]
    )

    try:
        texto = resposta.content[0].text.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        resultado = json.loads(texto.strip())

        # Garante que novo_dominio está nos limites
        resultado["novo_dominio"] = max(0, min(100, resultado.get("novo_dominio", dominio_atual)))
        # Injeta campos calculados localmente (mais confiáveis que deixar Claude calcular)
        resultado["proxima_revisao"] = proxima_revisao
        resultado["velocidade"] = velocidade
        resultado["concluido"] = resultado["novo_dominio"] >= 90
        return resultado
    except Exception:
        delta = 15 if entendimento > 80 else (5 if entendimento >= 60 else -5)
        novo = max(0, min(100, dominio_atual + delta))
        return {
            "novo_dominio": novo,
            "funcionou": "",
            "nao_funcionou": "",
            "padroes": [],
            "proximo_passo": "Continue estudando",
            "ajuste_trilha": "",
            "nivel_recomendado": "intermediário",
            "mensagem_aluno": "Continue assim!",
            "proxima_revisao": proxima_revisao,
            "velocidade": velocidade,
            "concluido": novo >= 90
        }
