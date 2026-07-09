from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os

# Ajouter le répertoire parent au chemin d'importation pour Vercel
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from bbot import create_app

# Initialiser l'application Telegram globalement (persiste lors des démarrages à chaud)
app = create_app()

# Initialisation asynchrone unique de l'application
async def init_app():
    if not app.running:
        await app.initialize()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            update_dict = json.loads(post_data.decode('utf-8'))
            
            async def handle_update():
                await init_app()
                update = Update.de_json(update_dict, app.bot)
                await app.process_update(update)
            
            # Exécuter la boucle d'événements pour traiter la mise à jour
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(handle_update())
            finally:
                loop.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            
        except Exception as e:
            print("Erreur de traitement du webhook:", e)
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode('utf-8'))

    def do_GET(self):
        # Pour tester si l'endpoint répond
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write("Webhook endpoint is active. Send POST updates from Telegram here.".encode('utf-8'))
