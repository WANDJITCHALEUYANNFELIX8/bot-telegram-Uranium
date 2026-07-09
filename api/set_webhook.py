from http.server import BaseHTTPRequestHandler
import json
import asyncio
import urllib.parse
import sys
import os

# Ajouter le répertoire parent au chemin d'importation pour Vercel
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Bot
from bbot import TOKEN

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Récupérer l'URL à partir des paramètres de requête ou la détecter automatiquement
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        custom_url = query_components.get('url', [None])[0]
        
        host = self.headers.get('Host')
        
        if custom_url:
            webhook_url = f"{custom_url.rstrip('/')}/api/webhook"
        elif host:
            # Gérer localhost ou les domaines Vercel
            protocol = "http" if "localhost" in host or "127.0.0.1" in host else "https"
            webhook_url = f"{protocol}://{host}/api/webhook"
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Error: Host header not found. Please provide URL parameter (e.g. ?url=https://your-domain.vercel.app)".encode('utf-8'))
            return

        async def register_webhook():
            bot = Bot(token=TOKEN)
            # Enregistrer l'URL du webhook auprès de Telegram
            success = await bot.set_webhook(url=webhook_url)
            info = await bot.get_webhook_info()
            return success, info

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success, info = loop.run_until_complete(register_webhook())
            finally:
                loop.close()

            response_data = {
                "success": success,
                "webhook_url_set": webhook_url,
                "telegram_webhook_info": {
                    "url": info.url,
                    "has_custom_certificate": info.has_custom_certificate,
                    "pending_update_count": info.pending_update_count,
                    "ip_address": info.ip_address,
                    "last_error_date": info.last_error_date,
                    "last_error_message": info.last_error_message,
                    "max_connections": info.max_connections,
                    "allowed_updates": info.allowed_updates
                }
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, indent=4).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error setting webhook: {e}".encode('utf-8'))
