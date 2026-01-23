import os
from dotenv import load_dotenv
import json
import asyncio
import aiohttp
from io import BytesIO
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
import random
from random import choice
import shlex
import requests
from openai import OpenAI
from google import genai
from google.genai import types
from googleapiclient.discovery import build
from textblob import TextBlob
from deep_translator import GoogleTranslator

# ================= CONFIGURATION =================
dotenv_path = os.getenv("DOTENV_PATH", "/home/uranium_yann/Github/bbot_telegram/.env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"💡 Chargement des variables depuis : {dotenv_path}")
else:
    print("💡 Aucun fichier .env trouvé, utilisation des variables d'environnement du système.")

# Variables d'environnement
NASA_API = os.getenv("NASA_API0")
HF_API = os.getenv("HF_API0")
MONEY_API = os.getenv("MONEY_API0")
METEO_API = os.getenv("METEO_API0")
ADMIN_ID = os.getenv("ADMIN_ID0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY0")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY0")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY0")
TOKEN = os.getenv("TOKEN0")
USERS_FILE = "users0.json"
client = OpenAI(api_key=OPENAI_API_KEY)

if not TOKEN:
    raise ValueError("❌ Erreur : TELEGRAM_TOKEN introuvable ! Vérifie .env ou la variable Railway.")

# Chargement des utilisateurs
users0 = {}
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            users0 = json.load(f)
        except json.JSONDecodeError:
            users0 = {}

# ================= FONCTIONS UTILITAIRES =================

def save_users():
    """Sauvegarde les utilisateurs dans le fichier JSON"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users0, f, indent=4, ensure_ascii=False)

# ================= COMMANDES TELEGRAM =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande de démarrage"""
    user = update.message.from_user
    users0[str(user.id)] = {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "user_name": user.username or ""
    }
    save_users()
    
    await update.message.reply_text(
        f"Salut! Je suis Uranium.\n"
        f"BRAVO {user.first_name}! Tu as été enregistré dans ma base de données.\n"
        f"Entre /man pour découvrir mon potentiel."
    )

async def man(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manuel d'utilisation"""
    help_text = """
🌋 === URANIUM BOT - MANUEL ===

📊 MATHÉMATIQUES
1. /addition nombre1 nombre2...
2. /sous nombre1 nombre2
3. /produit nombre1 nombre2
4. /div nombre1 nombre2
5. /modulo nombre1 nombre2
6. /exp nombre exposant

💬 CONVERSATION & INFOS
7. /bonjour - Discuter avec le bot
8. /time - Heure et date actuelle
9. /online - Vérifier si le bot est en ligne
10. /conseil - Conseil du jour
✅ 11. /versetBiblique - Verset biblique du jour

🎵 MÉDIAS & IA
12. /video <sujet> - Meilleures vidéos YouTube
13. /generate <question> - Poser des questions à Gemini
14. /image <description> - Générer une image IA
15. /generate_image <description> - Générer une image IA

🌍 SERVICES
15. /meteo <ville> - Météo d'une ville
16. /traduire <langue> <texte> - Traduire un texte
17. /convertir <montant> <devise1> <devise2> - Convertir des devises
18. /astro [astre] - Image du jour ou info sur un astre

⏰ RAPPELS & MESSAGES
19. /rappel <temps> <message> - Créer un rappel (ex: /rappel 10m réunion)
20. /send @nom message - Envoyer un message à un utilisateur
21. /listen - Liste des utilisateurs enregistrés

👑 ADMIN SEULEMENT
22. /broadcast <message> - Envoyer un message à tous
"""
    await update.message.reply_text(help_text)

# ================= MATHÉMATIQUES =================

async def addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Addition de plusieurs nombres"""
    try:
        if not context.args:
            await update.message.reply_text("Utilisation: /addition nombre1 nombre2 ...")
            return
        nombres = [float(a) for a in context.args]
        resultat = sum(nombres)
        await update.message.reply_text(f"Le résultat est: {resultat}")
    except ValueError:
        await update.message.reply_text("❌ Erreur: entrez des nombres valides.")

async def sous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Soustraction de deux nombres"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Utilisation: /sous nombre1 nombre2")
            return
        nbre1, nbre2 = map(float, context.args)
        res = nbre1 - nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("❌ Erreur: entrez deux nombres valides.")

async def produit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Produit de deux nombres"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Utilisation: /produit nombre1 nombre2")
            return
        nbre1, nbre2 = map(float, context.args)
        res = nbre1 * nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("❌ Erreur: entrez deux nombres valides.")

async def div(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Division de deux nombres"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Utilisation: /div nombre1 nombre2")
            return
        nbre1, nbre2 = map(float, context.args)
        if nbre2 == 0:
            await update.message.reply_text("❌ Erreur: division par zéro.")
            return
        res = nbre1 / nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("❌ Erreur: entrez deux nombres valides.")

async def modulo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Modulo de deux nombres"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Utilisation: /modulo nombre1 nombre2")
            return
        nbre1, nbre2 = map(int, context.args)
        if nbre2 == 0:
            await update.message.reply_text("❌ Erreur: division par zéro.")
            return
        res = nbre1 % nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("❌ Erreur: entrez deux entiers valides.")

async def exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exponentiation"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Utilisation: /exp nombre exposant")
            return
        nbre1, nbre2 = map(float, context.args)
        res = nbre1 ** nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("❌ Erreur: entrez deux nombres valides.")
    except OverflowError:
        await update.message.reply_text("❌ Erreur: le résultat est trop grand.")

# ================= TEMPS & INFORMATIONS =================

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche l'heure et la date actuelles"""
    now = datetime.now()
    heure = now.strftime("%H:%M:%S")
    date = now.strftime("%d/%m/%Y")
    await update.message.reply_text(f"⏰ Heure actuelle: {heure}\n📅 Date actuelle: {date}")

async def online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vérifie si le bot est en ligne"""
    await update.message.chat.send_action(action=ChatAction.TYPING)
    await asyncio.sleep(1)
    await update.message.reply_text("✅ URANIUM est en ligne et opérationnel!")

# ================= CONVERSATION =================

async def bonjour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestion des conversations"""
    text = update.message.text.lower()
    bot_username = context.bot.username.lower() if context.bot.username else ""

    # En groupe, ignorer si le bot n'est pas mentionné
    if update.message.chat.type != 'private' and f"@{bot_username}" not in text:
        return

    text = text.replace(f"@{bot_username}", "").strip()
    
    # Réponses prédéfinies
    responses = {
        "bonjour": "Salut! Comment tu vas?",
        "salut": "Salut! Comment tu vas?",
        "je vais bien": "Je vais bien aussi merci.",
        "idiot": "Évitons les mots violents s'il te plaît.",
        "ton nom": "Je m'appelle URANIUM!",
        "quel est ton nom": "Je m'appelle URANIUM!",
        "tu t'appelles comment": "Je m'appelle URANIUM!",
        "merci": "C'était un plaisir de collaborer avec toi!",
        "clé api": "Désolé mais nous ne divulguons pas ce genre d'informations.",
        "token": "Désolé mais nous ne divulguons pas ce genre d'informations.",
        "créateur": "Une divinité de Konoha 🌸",
        "ton créateur": "Une divinité de Konoha 🌸",
        "qui t'a créé": "Une divinité de Konoha 🌸",
        "aurevoir": "À très bientôt 👋",
        "bye": "À très bientôt 👋"
    }
    
    # Recherche de correspondance
    for key, response in responses.items():
        if key in text:
            await update.message.reply_text(response)
            return
    
    # Réponse par défaut
    default_responses = [
        "Bien!",
        "Faut toujours prier avant tout.",
        "Lis le Psaume 23. C'est dans la Bible.",
        "L'école doit être ta priorité.",
        "Intéressant! Dis-m'en plus."
    ]
    await update.message.reply_text(choice(default_responses))

# ================= VERSETS BIBLIQUES & CONSEILS =================

async def versetBiblique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verset biblique aléatoire"""
    versets = [
        "Psaumes 119:11\nJe garde ta parole tout au fond de mon cœur afin de ne point pécher contre toi.",
        "Psaumes 23:1\nCantique de David. L'Éternel est mon berger je ne manquerai de rien.",
        "Psaumes 24:7\nPortes, élevez vos linteaux; élevez-vous portes éternelles! Que le roi de gloire fasse son entrée.",
        "Proverbes 7:4\nDis à la sagesse: tu es ma sœur! Et appelle l'intelligence ton amie.",
        "Proverbes 10:27\nLa crainte de l'Éternel augmente les jours mais les années des méchants sont abrégées.",
        "Proverbes 10:2\nLes trésors de la méchanceté ne profitent pas, mais la justice délivre de la mort.",
        "Proverbes 10:4\nCelui qui agit d'une main lâche s'appauvrit, mais la main des diligents enrichit.",
        "Proverbes 10:7\nLa mémoire du juste est en bénédiction, mais le nom des méchants tombe en pourriture.",
        "Proverbes 10:12\nLa haine excite les querelles, mais l'amour couvre toutes les fautes.",
        "Proverbes 10:14\nLes sages tiennent la science en réserve, mais la bouche de l'insensé est une ruine prochaine.",
        "Proverbes 10:16\nL'œuvre du juste est pour la vie, le gain du méchant est pour le péché.",
        "Romains 12:9\nQue l'amour soit sans hypocrisie. Ayez le mal en horreur; attachez-vous fortement au bien.",
        "Romains 12:14\nBénissez ceux qui vous persécutent, bénissez et ne maudissez pas.",
        "Apocalypse 22:21\nQue la grâce du Seigneur JÉSUS soit avec vous tous!"
    ]
    verset = choice(versets)
    await update.message.reply_text(f"✝️ {verset}\n\n🙏 Bonne méditation!")

async def conseil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Conseil du jour"""
    conseils = [
        "💡 Bois beaucoup d'eau aujourd'hui, ton corps te remerciera.",
        "📚 Lis au moins 10 pages d'un livre que tu aimes.",
        "💪 Fais un peu d'exercice, même 5 minutes c'est bon pour le moral.",
        "🧘‍♂️ Respire profondément 3 fois avant de répondre à quelqu'un.",
        "💰 Garde toujours 10% de ce que tu gagnes, peu importe le montant.",
        "📅 Note tes priorités du jour avant de commencer à travailler.",
        "🙏 Remercie quelqu'un aujourd'hui, même pour une petite chose.",
        "🌱 Ne te compare pas aux autres, progresse à ton rythme."
    ]
    conseil_du_jour = choice(conseils)
    await update.message.reply_text(f"✨ Conseil du jour :\n\n{conseil_du_jour}")

# ================= UTILISATEURS =================

async def listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Liste des utilisateurs enregistrés"""
    if not users0:
        await update.message.reply_text("📭 Aucun utilisateur enregistré.")
        return
    
    message = "👥 Liste des utilisateurs enregistrés :\n\n"
    for uid, info in users0.items():
        full_name = info.get("full_name", "Inconnu")
        username = info.get("user_name", "")
        uname = f"@{username}" if username else "Pas de username"
        message += f"• {full_name} (ID: {uid}, {uname})\n"
    
    await update.message.reply_text(message)

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envoyer un message à un utilisateur"""
    sender = update.message.from_user.full_name or "Utilisateur"
    args = shlex.split(update.message.text)
    
    if len(args) < 3:
        await update.message.reply_text("Utilisation: /send @nom_destinataire message")
        return
    
    destinataire = args[1].replace("@", "").strip()
    message_final = " ".join(args[2:])
    
    # Recherche de l'utilisateur
    desti_id = None
    for uid, info in users0.items():
        if info.get("full_name") == destinataire or info.get("user_name") == destinataire:
            desti_id = uid
            break
    
    if not desti_id:
        await update.message.reply_text(f"❌ Utilisateur '{destinataire}' introuvable.")
        return
    
    try:
        await context.bot.send_message(
            chat_id=int(desti_id), 
            text=f"💬 Message de {sender}:\n\n{message_final}"
        )
        await update.message.reply_text("✅ Message envoyé avec succès!")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur lors de l'envoi: {e}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Diffusion de message à tous les utilisateurs (admin uniquement)"""
    sender = update.message.from_user.first_name or "Admin"
    user_id = str(update.message.from_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé à effectuer cette opération.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Utilisation: /broadcast message")
        return
    
    message = " ".join(context.args)
    await update.message.reply_text("📡 Début de l'envoi des messages...")
    
    success = 0
    failed = 0
    
    for uid, info in users0.items():
        try:
            await context.bot.send_message(
                chat_id=uid, 
                text=f"📢 Message de {sender}:\n\n{message}"
            )
            success += 1
        except Exception as e:
            failed += 1
            print(f"Erreur d'envoi à {info.get('full_name', uid)}: {e}")
    
    await update.message.reply_text(
        f"✅ Envoi terminé!\n"
        f"• Réussis: {success}\n"
        f"• Échecs: {failed}"
    )

# ================= RAPPELS =================

async def envoyer_rappel(context: ContextTypes.DEFAULT_TYPE, user_id: int, message: str, delai: int):
    """Envoi différé d'un rappel"""
    try:
        await asyncio.sleep(delai)
        await context.bot.send_message(chat_id=user_id, text=f"⏰ Rappel : {message}")
    except Exception as e:
        print(f"Erreur en envoyant le rappel à {user_id} : {e}")

async def rappel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Créer un rappel"""
    user_id = update.message.from_user.id
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Utilisation: /rappel <temps> <message>\n"
            "Exemples: /rappel 30s Pause, /rappel 5m Réunion, /rappel 2h Rendez-vous"
        )
        return
    
    temps = context.args[0].lower()
    message = " ".join(context.args[1:])
    
    try:
        if temps.endswith("s"):
            delai = int(temps[:-1])
        elif temps.endswith("m"):
            delai = int(temps[:-1]) * 60
        elif temps.endswith("h"):
            delai = int(temps[:-1]) * 3600
        else:
            await update.message.reply_text("❌ Format invalide. Utilisez: s (secondes), m (minutes), h (heures)")
            return
    except ValueError:
        await update.message.reply_text("❌ Temps invalide. Exemple: 10s, 5m, 2h")
        return
    
    context.application.create_task(envoyer_rappel(context, user_id, message, delai))
    await update.message.reply_text(f"✅ Rappel enregistré dans {temps}: {message}")

# ================= SERVICES EXTERNES =================

async def meteo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Météo d'une ville"""
    if not METEO_API:
        await update.message.reply_text("❌ Clé API météo manquante.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Utilisation: /meteo <nom_ville>")
        return
    
    ville = " ".join(context.args)
    lien = f"http://api.openweathermap.org/data/2.5/weather?q={ville}&appid={METEO_API}&units=metric&lang=fr"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(lien) as response:
                if response.status != 200:
                    await update.message.reply_text(f"❌ Impossible de récupérer la météo de: {ville}")
                    return
                data = await response.json()
        
        temp = data["main"]["temp"]
        humidite = data["main"]["humidity"]
        condition = data["weather"][0]["description"]
        
        await update.message.reply_text(
            f"🌤 Météo pour {ville}:\n"
            f"🌡 Température: {temp}°C\n"
            f"💧 Humidité: {humidite}%\n"
            f"☁️ Condition: {condition.capitalize()}"
        )
    except Exception as e:
        print(f"Erreur météo: {e}")
        await update.message.reply_text("❌ Erreur lors de la récupération de la météo.")

async def traduire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traduction de texte"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Utilisation: /traduire <langue> <texte>\n"
            "Langues: en (anglais), fr (français), es (espagnol), de (allemand), ja (japonais), it (italien), ar (arabe)..."
        )
        return
    
    langue = context.args[0].lower()
    texte = " ".join(context.args[1:])
    
    try:
        res = GoogleTranslator(source='auto', target=langue).translate(texte)
        await update.message.reply_text(f"🌐 Traduction ({langue}):\n\n{res}")
    except Exception as e:
        print(f"Erreur traduction: {e}")
        await update.message.reply_text("❌ Erreur de traduction. Vérifiez le code langue (2 lettres).")

async def convertir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Conversion de devises"""
    if not MONEY_API:
        await update.message.reply_text("❌ Clé API de conversion manquante.")
        return
    
    if len(context.args) != 3:
        await update.message.reply_text(
            "Utilisation: /convertir <montant> <devise1> <devise2>\n"
            "Exemple: /convertir 100 USD EUR"
        )
        return
    
    try:
        montant = float(context.args[0])
        monnaie_deb = context.args[1].upper()
        monnaie_fin = context.args[2].upper()
        
        lien = f"https://api.apilayer.com/exchangerates_data/convert?from={monnaie_deb}&to={monnaie_fin}&amount={montant}"
        headers = {"apikey": MONEY_API}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(lien, headers=headers) as response:
                if response.status != 200:
                    await update.message.reply_text("❌ Impossible de récupérer la conversion.")
                    return
                data = await response.json()
                
                if not data.get("success", True):
                    await update.message.reply_text("❌ Conversion échouée. Vérifiez les devises.")
                    return
        
        res = data.get("result")
        await update.message.reply_text(f"💱 {montant} {monnaie_deb} = {res:.2f} {monnaie_fin}")
    
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
    except Exception as e:
        print(f"Erreur conversion: {e}")
        await update.message.reply_text("❌ Erreur lors de la conversion.")

# ================= INTELLIGENCE ARTIFICIELLE =================

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Génération de texte avec Gemini"""
    if not GEMINI_API_KEY:
        await update.message.reply_text("❌ Clé API Gemini manquante.")
        return
    
    if not context.args:
        await update.message.reply_text("Utilisation: /generate <votre question>")
        return
    
    text = " ".join(context.args)
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=text
        )
        output = response.text.strip()
        await update.message.reply_text(output)
    except Exception as e:
        print(f"Erreur Gemini: {e}")
        await update.message.reply_text(f"❌ Erreur lors de la génération: {e}")

async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Génération d'image avec Stable Diffusion"""
    if not HF_API:
        await update.message.reply_text("❌ Clé API Hugging Face manquante.")
        return
    
    if not context.args:
        await update.message.reply_text("Utilisation: /image <description>")
        return
    
    prompt = " ".join(context.args)
    await update.message.reply_text(f"🎨 Création de l'image pour: {prompt}")
    
    try:
        lien = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {HF_API}"}
        payload = {"inputs": prompt, "options": {"wait_for_model": True}}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(lien, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    if "estimated_time" in error_text:
                        await update.message.reply_text("⏳ Modèle en chargement. Réessayez dans 1-2 minutes.")
                    else:
                        await update.message.reply_text("❌ Impossible de générer l'image.")
                    return
                
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    error_data = await response.json()
                    await update.message.reply_text(f"❌ Erreur: {error_data}")
                    return
                
                image_bytes = await response.read()
                if len(image_bytes) < 100:
                    await update.message.reply_text("❌ Image générée invalide.")
                    return
                
                image_buffer = BytesIO(image_bytes)
                image_buffer.name = "image.png"
                await update.message.reply_photo(photo=image_buffer, caption=f"🎨 {prompt}")
    
    except Exception as e:
        print(f"Erreur génération image: {e}")
        await update.message.reply_text("❌ Erreur lors de la création de l'image.")

# ================= YOUTUBE =================

async def search_video(query: str):
    """Recherche de vidéos YouTube"""
    if not YOUTUBE_API_KEY:
        return []
    
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(part="snippet", q=query, type="video", maxResults=10)
    response = request.execute()
    
    videos = []
    for item in response["items"]:
        video_id = item["id"]["videoId"]
        video_title = item["snippet"]["title"]
        videos.append((video_id, video_title))
    
    return videos

async def get_comments(video_id: str, maxComment: int = 100):
    """Récupération des commentaires YouTube"""
    if not YOUTUBE_API_KEY:
        return []
    
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    comments = []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            maxResults=100
        )
        
        while request and len(comments) < maxComment:
            response = request.execute()
            for item in response["items"]:
                textDisplay = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(textDisplay)
                if len(comments) >= maxComment:
                    break
            request = youtube.commentThreads().list_next(request, response)
    except Exception as e:
        print(f"Erreur récupération commentaires: {e}")
    
    return comments

async def analyze_comments(comments: list):
    """Analyse de commentaires"""
    if not comments:
        return 0
    total = 0
    for comment in comments:
        note = TextBlob(comment).sentiment.polarity
        total += note

    return total / len(comments)    
async def generate_score(update: Update, comments: list, n: int = 10):
    """Génération d'un résumé IA des commentaires"""
    if not comments:
        await update.message.reply_text("Aucun commentaire disponible.")
    return        
    if not GEMINI_API_KEY:
        await update.message.reply_text("❌ Clé API Gemini manquante.")
        return

    # Échantillon de commentaires
    sample_comments = random.sample(comments, min(n, len(comments)))
    await update.message.reply_text("--- Extraits de commentaires ---")
    for i, c in enumerate(sample_comments, 1):
        await update.message.reply_text(f"{i}. {c}")

    # Résumé IA
    client = genai.Client(api_key=GEMINI_API_KEY)
    comments_to_send = comments[:50]
    text_input = (
        "Voici une liste de commentaires YouTube. "
        "Fais un résumé global de ce que disent les spectateurs "
        "(points positifs, points négatifs, ambiance générale):\n\n"
        + "\n".join(comments_to_send)
    )

    await update.message.reply_text("--- Résumé IA ---")

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=text_input
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur lors de l'analyse IA: {e}")    

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recherche et analyse de vidéos YouTube"""
    if not YOUTUBE_API_KEY:
        await update.message.reply_text("❌ Clé API YouTube manquante.")
        return        

    await update.message.chat.send_action(action=ChatAction.TYPING)

    if not context.args:
        await update.message.reply_text("Utilisation: /video <sujet>")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Recherche des vidéos pour: {query}...")

    videos = await search_video(query)
    if not videos:
        await update.message.reply_text("Aucune vidéo trouvée.")
        return

    best_analyze = -999999
    best_video = None
    all_comments = []

    for video_id, video_title in videos:
        print(f"Analyse de la vidéo: {video_title}")
        comments = await get_comments(video_id, maxComment=100)
        if not comments:
            continue
    
        all_comments.extend(comments)
        score = await analyze_comments(comments)
        print(f"Score moyen: {score:.2f}")
    
        if score > best_analyze:
            best_analyze = score
            best_video = video_id

    # Résumé IA
    if all_comments:
        await generate_score(update, all_comments[:100], n=10)

    # Meilleure vidéo
    if best_video:
        await update.message.reply_text(
            f"🏆 Meilleure vidéo après analyse:\n"
            f"https://www.youtube.com/watch?v={best_video}\n"
            f"📊 Score: {best_analyze:.2f}"
        )
    else:
        await update.message.reply_text("Impossible de déterminer la meilleure vidéo.")     
           
#================= ASTRONOMIE =================
async def astro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Image astronomique du jour ou infos sur un astre"""
    if not NASA_API:
        await update.message.reply_text("❌ Clé API NASA manquante.")
        return        
    if not context.args:
        # Image du jour
        try:
            date_jour = datetime.now().strftime("%Y-%m-%d")
            lien = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API}&date={date_jour}"
            await update.message.reply_text("🔭 Récupération de l'image astronomique du jour...")
        
            async with aiohttp.ClientSession() as session:
                async with session.get(lien) as response:
                    if response.status != 200:
                        await update.message.reply_text("❌ Impossible de récupérer l'image.")
                        return
                    data = await response.json()
        
            titre = data.get("title", "Sans titre")
            description = data.get("explanation", "Pas de description")
            url = data.get("hdurl") or data.get("url")
            media_type = data.get("media_type", "image")
            date = data.get("date", date_jour)
            credit = data.get("copyright", "NASA/APOD")
        
            if media_type == "image":
                await update.message.reply_photo(
                    photo=url,
                    caption=f"🌌 *{titre}* — {date}\n📸 {credit}\n\n{description}",
                    parse_mode="Markdown"
                )
            elif media_type == "video":
                await update.message.reply_text(
                    f"🎥 *{titre}* — {date}\n🔗 {url}\n\n{description}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("Type de média inconnu.")
    
        except Exception as e:
            print(f"Erreur APOD: {e}")
            await update.message.reply_text("❌ Erreur de récupération des données astronomiques.")

    else:
        # Infos sur un astre
        astre = " ".join(context.args).lower()
        await update.message.reply_text(f"🔭 Récupération des informations sur {astre}...")
    
        lien = f"https://api.le-systeme-solaire.net/rest/bodies/{astre}"
    
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(lien) as response:
                    if response.status != 200:
                        await update.message.reply_text(f"❌ Impossible de trouver l'astre '{astre}'.")
                        return
                    data = await response.json()
                
                    if "englishName" not in data:
                        await update.message.reply_text(f"❌ Aucune information trouvée pour '{astre}'.")
                        return
        
            nom = data.get("englishName", "Inconnu")
            type_astre = data.get("bodyType", "Inconnu")
            gravite = data.get("gravity", "n.c.")
            masse = data.get("mass", {}).get("massValue", "n.c.")
            masse_exp = data.get("mass", {}).get("massExponent", "")
            rayon = data.get("meanRadius", "n.c.")
        
            texte = (
                f"🌠 *{nom}* ({type_astre})\n\n"
                f"🪶 Gravité: {gravite} m/s²\n"
                f"🌍 Masse: {masse} ×10^{masse_exp} kg\n"
                f"📏 Rayon moyen: {rayon} km"
            )
            await update.message.reply_text(texte, parse_mode="Markdown")
    
        except Exception as e:
            print(f"Erreur infos astre: {e}")
            await update.message.reply_text("❌ Erreur de récupération des informations astronomiques.")   
        
#================= INITIALISATION & SIGNAL =================
async def signal(application: Application):
    """Signal de démarrage du bot"""
    if ADMIN_ID:
        try:
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text="✅ Le bot URANIUM est maintenant en ligne et prêt à répondre!"
            )
        except Exception as e:
            print(f"Erreur lors de l'envoi du signal: {e}")
#=================GENERATEUR IMAGE===========
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    await update.message.reply_text("🎨 Génération de l'image en cours...")

    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        image_url = response.data[0].url

        await update.message.reply_photo(photo=image_url, caption="🖼 Image générée")

    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")
    
#================= MAIN =================
def main():
    """Fonction principale"""
    app=Application.builder().token(TOKEN).post_init(signal).build()        
    # Commandes de base
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("man", man))
    app.add_handler(CommandHandler("online", online))
    app.add_handler(CommandHandler("time", time))

    # Mathématiques
    app.add_handler(CommandHandler("addition", addition))
    app.add_handler(CommandHandler("sous", sous))
    app.add_handler(CommandHandler("produit", produit))
    app.add_handler(CommandHandler("div", div))
    app.add_handler(CommandHandler("modulo", modulo))
    app.add_handler(CommandHandler("exp", exp))

    # Conversation & inspiration
    app.add_handler(CommandHandler("versetBiblique", versetBiblique))
    app.add_handler(CommandHandler("conseil", conseil))

    # Utilisateurs
    app.add_handler(CommandHandler("listen", listen))
    app.add_handler(CommandHandler("send", send))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Rappels
    app.add_handler(CommandHandler("rappel", rappel))

    # Services externes
    app.add_handler(CommandHandler("meteo", meteo))
    app.add_handler(CommandHandler("traduire", traduire))
    app.add_handler(CommandHandler("convertir", convertir))

    # IA
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("image", image))
    app.add_handler(CommandHandler("generate_image", generate_image))

    # Médias
    app.add_handler(CommandHandler("video", video))
    app.add_handler(CommandHandler("astro", astro))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bonjour))

    print("🤖 URANIUM en cours d'exécution...")
    app.run_polling()        
if __name__ == "__main__":
    main()
        
        
