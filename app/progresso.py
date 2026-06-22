import anthropic
import json
from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def gerar_analise_progresso(perfil: dict, streak: int, dias_sem_estudo: int) -> dict:
    """
    Recebe o perfil completo do aluno e gera análise personalizada:
    - próxima missão do dia
    - revisões recomendadas (repetição espaçada)
    - análise dos erros recorrentes
    - mensagem motivacional
    """
    perfil_str = json.dumps(perfil, ensure_ascii=False, indent=2)

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""Você é responsável por manter o aluno engajado e melhorar retenção.

Perfil do aluno:
{perfil_str}

Streak atual: {streak} dias
Dias sem estudar: {dias_sem_estudo}

Regras:
- Tema com domínio < 70% → agendar revisão urgente
- Erro recorrente em algum tema → priorizar reforço
- {f'Aluno ficou {dias_sem_estudo} dias sem estudar → sugerir retomada suave' if dias_sem_estudo >= 3 else 'Aluno está em dia com os estudos'}

Retorne APENAS um JSON válido:
{{
  "proxima_missao": {{
    "tema": "Nome do tema para estudar hoje",
    "acao": "O que exatamente fazer (assistir vídeo de X, praticar Y exercícios)",
    "tempo_estimado": "30min",
    "motivo": "Por que esse é o foco hoje"
  }},
  "revisoes_agendadas": [
    {{
      "tema": "Nome do tema",
      "urgencia": "hoje | esta semana | próxima semana",
      "motivo": "Domínio em X% — abaixo do ideal",
      "dominio": 45
    }}
  ],
  "principais_dificuldades": [
    "Padrão de erro ou dificuldade detectada"
  ],
  "ranking_dominio": [
    {{"tema": "Nome", "dominio": 85}},
    {{"tema": "Nome", "dominio": 60}}
  ],
  "mensagem": "Frase curta e motivacional personalizada para o aluno (1-2 frases)",
  "alerta": "null ou mensagem de alerta se houver algo crítico (ex: 3+ dias sem estudar)"
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
        return json.loads(texto.strip())
    except Exception:
        return {
            "proxima_missao": {"tema": "", "acao": "Continue de onde parou", "tempo_estimado": "", "motivo": ""},
            "revisoes_agendadas": [],
            "principais_dificuldades": [],
            "ranking_dominio": [],
            "mensagem": "Continue estudando!",
            "alerta": None
        }
