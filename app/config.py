import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
YOUTUBE_API_KEY   = os.getenv("YOUTUBE_API_KEY")

# Tokens premium: lista separada por vírgula no env var
# Ex: PREMIUM_TOKENS=SAI-AB12-CD34,SAI-EF56-GH78
_tokens_raw = os.getenv("PREMIUM_TOKENS", "")
PREMIUM_TOKENS: set[str] = {t.strip() for t in _tokens_raw.split(",") if t.strip()}

# Chave do admin para gerar tokens
ADMIN_KEY = os.getenv("ADMIN_KEY", "")

# Link de pagamento Mercado Pago (criar em mercadopago.com.br → Link de pagamento)
MP_LINK = os.getenv("MP_LINK", "#")

# Seu WhatsApp Business (formato: 5511999999999)
WHATSAPP = os.getenv("WHATSAPP", "")
