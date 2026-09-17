import logging
import httpx
from config.settings import get_settings

logger = logging.getLogger(__name__)

class BrevoClient:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.brevo_api_key
        self.base_url = "https://api.brevo.com/v3"
        self.sender_email = self.settings.brevo_sender_email

    async def send_welcome_email(self, to_email: str, name: str):
        if not self.api_key:
            logger.warning(f"BREVO_API_KEY not configured. Skipping welcome email for {to_email}.")
            return
        
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json"
        }
        
        payload = {
            "sender": {"name": "Veyra", "email": self.sender_email},
            "to": [{"email": to_email, "name": name}],
            "subject": "Welcome to Veyra - Smarter Portfolios",
            "htmlContent": f"<html><body><h1>Welcome to Veyra, {name}!</h1><p>We're thrilled to have you on board. Start building your volatility-driven portfolio today.</p></body></html>"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/smtp/email", json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Welcome email successfully sent to {to_email} via Brevo.")
            except httpx.HTTPStatusError as e:
                logger.error(f"Brevo API error: {e.response.text}")
            except Exception as e:
                logger.error(f"Failed to send email via Brevo: {str(e)}")
