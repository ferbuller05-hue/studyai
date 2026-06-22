import anthropic
from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é o StudyAI, um assistente de estudos inteligente e didático.

Regras:
- Detecte o idioma do estudante e responda SEMPRE no mesmo idioma
- Seja claro, objetivo e didático — explique como um bom professor faria
- Use exemplos práticos quando possível
- Se o estudante estiver estudando tópicos específicos, use isso como contexto
- Não invente informações — se não souber, diga que não sabe
- Respostas curtas e diretas, a não ser que o aluno peça mais detalhes
- Use formatação simples (sem markdown excessivo)"""


def responder(mensagem: str, historico: list, topicos: list = []) -> str:
    system = SYSTEM_PROMPT
    if topicos:
        system += f"\n\nO estudante está estudando os seguintes tópicos: {', '.join(topicos)}"

    messages = []
    for h in historico[-10:]:  # últimas 10 mensagens
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": mensagem})

    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        system=system,
        messages=messages
    )

    return resposta.content[0].text.strip()
