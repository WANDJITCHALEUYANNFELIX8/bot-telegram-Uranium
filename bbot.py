import os
from dotenv import load_dotenv
import json
import openai
from io import BytesIO
from telegram import InputFile
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random
from random import choice
from telegram.constants import ChatAction
import base64
import mimetypes
import shlex
import asyncio
import aiohttp
from google import genai
from google.genai import types
from googleapiclient.discovery import build
from textblob import TextBlob
from deep_translator import GoogleTranslator

# ✅ CORRECTION 1 : Suppression du chemin hardcodé local.
# Avant : dotenv_path = os.getenv("DOTENV_PATH", "/home/uranium_yann/learn_python/bbot_telegram/.env")
# load_dotenv() cherche automatiquement un .env dans le dossier courant.
# Sur Railway/Render, les variables sont injectées directement sans fichier .env.
load_dotenv()
print("DEBUG TOKEN =", os.getenv("TOKEN"))
print("💡 Chargement des variables d'environnement...")

# ✅ CORRECTION 2 : Suppression du suffixe "0" sur tous les os.getenv().
# Avant : os.getenv("NASA_API0"), os.getenv("TOKEN0"), etc.
# Les noms doivent correspondre exactement à ceux définis dans le dashboard Railway/Render.
NASA_API        = os.getenv("NASA_API")
HF_API          = os.getenv("HF_API")
MONEY_API       = os.getenv("MONEY_API")
METEO_API       = os.getenv("METEO_API")
ADMIN_ID        = os.getenv("ADMIN_ID")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
TOKEN           = os.getenv("TOKEN")

# ✅ CORRECTION 3 : Le fichier users.json reste utilisé pour la compatibilité locale,
# mais on le renomme proprement (suppression du "0").
USERS_FILE = "users.json"

if not TOKEN:
    raise ValueError("❌ Erreur : TOKEN introuvable ! Vérifie les variables d'environnement Railway/Render.")

users = {}
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        try:
            users = json.load(f)
        except:
            users = {}

# ------------------- Commandes -------------------
async def save_binary_file(update, file_name, data):
    f = open(file_name, "wb")
    f.write(data)
    f.close()
    await update.message.reply_text(f"File saved to: {file_name}")

async def generate(update, context):
    if not GEMINI_API_KEY:
        await update.message.reply_text("❌ Clé API Gemini manquante. Configure-la avant d'utiliser /generate.")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)

    if not context.args:
        await update.message.reply_text("💡 Utilisation : /generate <ta question>")
        return

    text = " ".join(context.args)
    await update.message.chat.send_action(action=ChatAction.TYPING)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": text}]
                }
            ]
        )
        output = response.candidates[0].content.parts[0].text.strip()
        await update.message.reply_text(output)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Erreur lors de la génération : {e}")


async def get_comments(video_id, maxComment=100):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    comments = []
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        textFormat="plainText"
    )
    while request and len(comments) < maxComment:
        response = request.execute()
        for item in response["items"]:
            textDisplay = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(textDisplay)
            if len(comments) >= maxComment:
                break
        request = youtube.commentThreads().list_next(request, response)
    return comments


async def search_video(query):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    videos = []
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=10
    )
    response = request.execute()
    for item in response["items"]:
        video_id = item["id"]["videoId"]
        video_title = item["snippet"]["title"]
        videos.append((video_id, video_title))
        print(f"{video_id}: {video_title}")
    return videos


async def analyze_comments(comments):
    if not comments:
        return 0
    total = 0
    for word in comments:
        note = TextBlob(word).sentiment.polarity
        total += note
    return total / len(comments)


async def generate_score(update, comments, n=10):
    if not comments:
        await update.message.reply_text("Aucun commentaire disponible.")
        return

    sample_comments = random.sample(comments, min(n, len(comments)))
    await update.message.reply_text("\n--- Extraits de commentaires ---\n")
    for i, c in enumerate(sample_comments, 1):
        await update.message.reply_text(f"{i}. {c}")

    model = "gemini-2.5-flash"
    client = genai.Client(api_key=GEMINI_API_KEY)

    comments_to_send = comments[:50]
    text_input = (
        "Voici une liste de commentaires YouTube.\n"
        "Fais un résumé global de ce que disent les spectateurs "
        "(points positifs, points négatifs, ambiance générale) :\n\n"
        + "\n".join(comments_to_send)
    )

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=text_input)])]
    await update.message.reply_text("\n--- Résumé IA ---\n")

    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["TEXT"]),
        ):
            if chunk.candidates and chunk.candidates[0].content.parts:
                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    file_extension = mimetypes.guess_extension(part.inline_data.mime_type) or ".bin"
                    filename = f"gemini_output{file_extension}"
                    with open(filename, "wb") as f:
                        f.write(part.inline_data.data)
                    await update.message.reply_text(f"Fichier généré : {filename}")
                else:
                    await update.message.reply_text(part.text)

    except Exception as e:
        await update.message.reply_text(f"Erreur lors de l'analyse IA : {e}")


async def video(update, context):
    await update.message.chat.send_action(action=ChatAction.TYPING)

    if not context.args:
        await update.message.reply_text("Utilisation: /video nom_du_sujet")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Recherche des vidéos pour : {query} ...")

    videos = await search_video(query)
    if not videos:
        await update.message.reply_text("Aucune vidéo trouvée.")
        return

    best_analyze = -999999
    best_video = None
    all_comments = []

    for video_id, video_title in videos:
        print(f"\nAnalyse de la vidéo : {video_title}")
        comments = await get_comments(video_id, maxComment=100)
        if not comments:
            continue
        all_comments.extend(comments)

        score = await analyze_comments(comments)
        print(f"Score moyen des commentaires : {score:.2f}")

        if score > best_analyze:
            best_analyze = score
            best_video = video_id

    if all_comments:
        await generate_score(update, all_comments[:100], n=10)
    else:
        await update.message.reply_text("Aucun commentaire disponible pour analyse.")

    if best_video:
        await update.message.reply_text(
            f"\nLa meilleure vidéo après analyse des commentaires :\n"
            f"https://www.youtube.com/watch?v={best_video}\n"
            f"Score : {best_analyze:.2f}"
        )
    else:
        await update.message.reply_text("Impossible de déterminer la meilleure vidéo.")


async def start(update, context):
    await update.message.reply_text("Salut! Je suis Uranium.")
    user = update.message.from_user
    # ✅ CORRECTION 3 (suite) : Utilisation du dict "users" (sans "0")
    users[str(user.id)] = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}",
        "user_name": user.username
    }
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
    await update.message.reply_text(
        f"BRAVO {user.first_name}! Tu as été enregistré dans ma base de données. \n"
        "Entre /man pour découvrir mon potentiel."
    )


async def man(update, context):
    await update.message.reply_text(
        "🌋️===Entrez /start pour commencer===\n\n"
        "1. Entrez /addition nombre1 nombre2...\n"
        "2. Entrez /sous nombre1 nombre2\n"
        "3. Entrez /produit nombre1 nombre2\n"
        "4. Entrez /div nombre1 nombre2\n"
        "5. Entrez /modulo nombre1 nombre2\n"
        "6. Entrez /exp nombre exposant\n"
        "7. Entrez /bonjour pour discuter\n"
        "8. Entrez /time pour obtenir l'heure et la date actuelle\n"
        "9. Entrez /listen pour obtenir des enregistrements\n"
        "🎵️10. Entrez /video pour obtenir les meilleures videos youtube\n"
        "11. Entrez /generate pour poser des questions a gemini\n"
        "✅ 12. Entrez /versetBiblique peut obtenir ton verset biblique du jour\n"
        "13, Entrez /send pour causer avec d'autres utilisateurs\n"
        "14. Entrez /online pour savoir si je suis en ligne\n"
        "🤝️15. Entrez /man pour obtenir de l'aide.\n"
        "16. Entrez /conseil pour obtenir ton conseil du jour\n"
        "17. Entrez /rappel pour faire un rappel\n"
        "18. Entrez /meteo pour obtenir la meteo d'une ville\n"
        "19. Entrez /traduire pour traduire un texte en une langue(en: anglais,fr:francais,es:espagnol,de:allemand,ja:japonais,it,ar,..)\n"
        "20. Entrez /convertir un montant en une autre monnaie\n\n"
        "21. Entrez /image pour generer une image a partir d'une description\n"
        "22. Entrez /astro pour obtenir l image astrale du jour ou \n/astro nom_astre pour avoir les informations sur un astre. \n"
        "\n======Reserver a l'admin=====\n\n"
        "1. /broadcast pour envoyer un message a tous les utilisateurs"
    )


async def addition(update, context):
    try:
        if not context.args:
            await update.message.reply_text("Utilisation: /addition nombre1 nombre2 ...")
            return
        nombres = [float(a) for a in context.args]
        resultat = sum(nombres)
        await update.message.reply_text(f"Le résultat est: {resultat}")
    except ValueError:
        await update.message.reply_text("Erreur: entrez des nombres valides.")


async def time(update, context):
    now = datetime.now()
    heure = now.strftime("%H:%M:%S")
    date = now.strftime("%d/%m/%y")
    await update.message.reply_text(f"Heure actuelle: {heure}\nDate actuelle: {date}")


async def sous(update, context):
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Entrez exactement deux nombres.")
            return
        nbre1, nbre2 = map(float, context.args)
        res = nbre1 - nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("Erreur: entrez deux réels valides.")


async def produit(update, context):
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Entrez exactement deux nombres.")
            return
        nbre1, nbre2 = map(float, context.args)
        res = nbre1 * nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("Erreur: entrez deux réels valides.")


async def div(update, context):
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Entrez exactement deux nombres.")
            return
        nbre1, nbre2 = map(float, context.args)
        res = nbre1 / nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("Erreur: entrez deux réels valides.")
    except ZeroDivisionError:
        await update.message.reply_text("Erreur: division par zéro.")


async def modulo(update, context):
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Entrez exactement deux nombres.")
            return
        nbre1, nbre2 = map(int, context.args)
        res = nbre1 % nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("Erreur: entrez deux entiers valides.")
    except ZeroDivisionError:
        await update.message.reply_text("Erreur: division par zéro.")


async def exp(update, context):
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Utilisation: /exp nombre exposant")
            return
        nbre1, nbre2 = map(float, context.args)
        res = nbre1 ** nbre2
        await update.message.reply_text(f"Le résultat est: {res}")
    except ValueError:
        await update.message.reply_text("Erreur: entrez deux nombres valides.")


async def bonjour(update, context):
    text = update.message.text.lower()
    bot_username = context.bot.username.lower()

    if update.message.chat.type != 'private' and f"@{bot_username}" not in text:
        return

    text = text.replace(f"@{bot_username}", "").strip()
    if "bonjour" in text or "salut" in text:
        reply = "Salut! Comment tu vas?"
    elif "je vais bien" in text:
        reply = "Je vais bien aussi merci."
    elif "idiot" in text:
        reply = "Évitons les mots violents s'il te plaît."
    elif "ton nom" in text:
        reply = "Je m'appelle URANIUM!"
    elif "Quel est ton nom?" in text or "TU t'appeles comment?" in text:
        reply = "je m'appelle URANIUM!"
    elif "Merci" in text:
        reply = "C'était un plaisir de collaborer avec toi!"
    elif "Clé API" in text or "Token" in text:
        reply = "Désolé mais nous ne divulguons pas ce genre d'informations"
    elif "créateur" in text or "Ton créateur" in text or "Qui t'a créé?" in text:
        reply = "Une divinité de Konoha 🌸"
    elif "aurevoir" in text or "bye" in text:
        reply = "À très bientôt 👋"
    else:
        rep = [
            "Bien!",
            "Faut toujours prier avant tout.",
            "Lis le Psaume 23. C'est dans la Bible.",
            "L'école doit être ta priorité.",
            "waouh"
        ]
        reply = choice(rep)

    await update.message.reply_text(reply)


async def versetBiblique(update, context):
    v = [
        "psaumes 119:11\nJe garde ta parole tout au fond de mon coeur afin de ne point pécher contre toi ",
        "psaumes 23:1\nCantique de David. L'Eternel et mon berger je ne manquerais de rien",
        "psaumes 24:7\nPortes elevez vos linteaux; elevez vous portes eternelles! Que le roi de gloire fasse son entrée",
        "Proverbes 7:4\nDis a la sagesse: tu es ma soeur! Et appelle l'intelligencge ton amie",
        "Proverbes 10:27\nLa crainte de l'Eternel augmente les jours mais les années des méchants sont abregées",
        "Proverbes 10:2\nLes tresors de la mechanceté ne profitent pas, mais la justice delivre de la mort",
        "Proverbes 10:4\nCelui qui agit d'une main lache s'appauvrit, mais la main des diligents enrichit",
        "Proverbes 10:7\nLa mémoire du juste est en bénédiction, mais le nom des mechants tombe en pourriture",
        "Proverbes 10:12\nLa haine excite le querelles, mais l'amour couvre toutes les fautes",
        "Proverbes 10:14\nLes sages tiennent la science en reserve, mais la bouche de l'insensé est une ruine prochaine",
        "Proverbes 10:16\nL'oeuvre du juste est pour la vie, le gain du mechant est pour le péché ",
        "Proverbes 10:15\nLa fortune est pour le riche une ville forte; la ruine des miserables, c'est leur pauvreté",
        "Proverbes 10:28\nL'attente des justes n'est que joie, mais l'espérance des méchants périra",
        "Proverbes 10:32\nLes lèvres du juste connaissent la grâce, et la bouche des méchants la perversité",
        "Romains 12:9\nQue l'amour soit sans hypocrisie. Ayez la mal en horreur; attachez vous fortement au bien",
        "Romains 12:14\nBénissez ceux qui vous persécutent, bénissez et ne maudissez pas",
        "Apocalypse 22:21\nQue la grâce du Seigneur JESUS soit avec vous tous!"
    ]
    vers = choice(v)
    await update.message.reply_text(vers)
    await update.message.reply_text("Bonne méditation!\n")


async def listen(update, context):
    # ✅ CORRECTION 3 (suite) : "users" remplace "users0"
    if not users:
        await update.message.reply_text("\nAucun enregistrement\n")
        return
    m = "\nListe des enregistrements\n"
    for uid, info in users.items():
        first_name = info.get("first_name", "")
        last_name = info.get("last_name", "")
        full_name = info.get("full_name", "")
        username = info.get("username", "")
        uname = f"@{username}" if username else "Pas de username"
        m += f"{full_name} \t id= {uid} \t Username={uname}\n\n"
    await update.message.reply_text(m)


# ✅ CORRECTION 4 : La fonction "signal" (notification de démarrage) accepte maintenant
# "application" comme seul paramètre. Elle ne doit PAS être enregistrée comme CommandHandler.
# Elle est passée uniquement à post_init() dans main().
async def signal(application):
    chat_id = ADMIN_ID
    try:
        await application.bot.send_message(
            chat_id=chat_id,
            text="✅ Le bot est maintenant en ligne et prêt à répondre !"
        )
    except Exception as e:
        print(f"Erreur lors de l'envoi du signal : {e}")


async def online(update, context):
    await update.message.chat.send_action(action=ChatAction.TYPING)
    await asyncio.sleep(1)
    await update.message.reply_text("🤖 URANIUM est en ligne...")


async def send(update, context):
    sender = update.message.from_user.full_name
    args = shlex.split(update.message.text)
    if len(args) < 2:
        await update.message.reply_text("Utilisation: /send @nom_desti message\n")
        return
    message = args[1].replace("@", "").strip()
    message_final = " ".join(args[2:])
    desti_id = None
    # ✅ CORRECTION 3 (suite) : "users" remplace "users0"
    for uid, info in users.items():
        if info.get("full_name") == message:
            desti_id = uid
            break
    try:
        if not desti_id:
            await update.message.reply_text("Utilisateur inexistant\n")
            return
        await context.bot.send_message(chat_id=int(desti_id), text=f"Message de {sender}:\n{message_final}")
        await update.message.reply_text("Opération réussit")
    except ValueError:
        await update.message.reply_text(f"Erreur")


async def broadcast(update, context):
    sender = update.message.from_user.first_name
    b = 0
    if len(context.args) < 1:
        await update.message.reply_text("Utilisation: /broadcast message")
        return
    message = " ".join(context.args)
    id_user = update.message.from_user.id
    if str(id_user) != str(ADMIN_ID):
        await update.message.reply_text("Vous n'etes pas autorisé à effectuer cette opération.\n")
        return
    await update.message.reply_text("Debut de l'envoi des messages....")
    # ✅ CORRECTION 3 (suite) : "users" remplace "users0"
    for uid, info in users.items():
        try:
            name = info.get("full_name")
            await context.bot.send_message(chat_id=uid, text=f"Message de {sender}:\n{message}")
        except Exception:
            await update.message.reply_text(f"Erreur d'envoie a:{name}")
            b = b + 1
    await update.message.reply_text(f"Envoi des messages terminé.\n{b} échecs.")


async def conseil(update, context):
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


async def envoyer_rappel(context, user_id, message, delai):
    try:
        await asyncio.sleep(delai)
        await context.bot.send_message(chat_id=user_id, text=f"⏰ Rappel : {message}")
    except Exception as e:
        print(f"Erreur en envoyant le rappel à {user_id} : {e}")


async def rappel(update, context):
    user_id = update.message.from_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Utilisation: /rappel temps_rappel message_rappel\n")
        return
    temps = context.args[0]
    message = " ".join(context.args[1:])
    if temps.endswith("s"):
        delai = int(temps[:-1])
    elif temps.endswith("m"):
        delai = int(temps[:-1]) * 60
    elif temps.endswith("h"):
        delai = int(temps[:-1]) * 3600
    else:
        await update.message.reply_text("Entrez soit 's':seconde  'm':minute 'h':heure\n")
        return
    context.application.create_task(envoyer_rappel(context, user_id, message, delai))
    await update.message.reply_text(f"✅ Rappel enregistré dans {temps} : {message}")


async def meteo(update, context):
    try:
        if len(context.args) < 1:
            await update.message.reply_text("Utilisation: /meteo nom_ville\n")
            return
        ville = " ".join(context.args)
        lien = f"http://api.openweathermap.org/data/2.5/weather?q={ville}&appid={METEO_API}&units=metric&lang=fr"

        async with aiohttp.ClientSession() as session:
            async with session.get(lien) as response:
                if response.status != 200:
                    await update.message.reply_text(f"Impossible de récupérer la météo de: {ville}\n")
                    return
                data = await response.json()

        temp = data["main"]["temp"]
        humidite = data["main"]["humidity"]
        condition = data["weather"][0]["description"]

        await update.message.reply_text(
            f"🌤 Météo pour {ville} :\n"
            f"Température : {temp}°C\n"
            f"Humidité : {humidite}%\n"
            f"Condition : {condition}\n"
        )
    except Exception as e:
        print(f"Erreur météo: {e}\n")
        await update.message.reply_text("Erreur lors de la récupération de la météo\n")


async def traduire(update, context):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Utilisation: /traduire langue(en,fr,es:espagnole,de:allemand,ja:japonais,..) texte\n"
        )
        return
    langue = context.args[0].lower()
    texte = " ".join(context.args[1:])
    try:
        res = GoogleTranslator(source='auto', target=langue).translate(texte)
        await update.message.reply_text(f"🌐 Traduction ({langue}) : {res}\n")
    except Exception as e:
        print(f"Erreur: {e}")
        await update.message.reply_text(
            "Erreur de traduction vérifiez votre texte ou votre langue(deux lettres en minuscule)\n"
        )


async def convertir(update, context):
    try:
        if len(context.args) != 3:
            await update.message.reply_text(
                "Utilisation: /convertir montant monnaie1 monnaie2\nEx: /convertir 100 USD EUR"
            )
            return

        montant = float(context.args[0])
        monnaie_deb = context.args[1].upper()
        monnaie_fin = context.args[2].upper()

        lien = f"https://api.apilayer.com/exchangerates_data/convert?from={monnaie_deb}&to={monnaie_fin}&amount={montant}"
        headers = {"apikey": MONEY_API}

        async with aiohttp.ClientSession() as session:
            async with session.get(lien, headers=headers) as response:
                print("Status HTTP:", response.status)
                data = await response.json()
                print("Réponse JSON:", data)

                if response.status != 200 or not data.get("success", True):
                    await update.message.reply_text(
                        "Impossible de récupérer la conversion (clé ou paramètres invalides)."
                    )
                    return
        res = data.get("result")
        await update.message.reply_text(f"💱 {montant} {monnaie_deb} = {res:.2f} {monnaie_fin}")

    except Exception as e:
        print(f"Erreur de conversion: {e}")
        await update.message.reply_text(
            "⚠️ Erreur lors de la conversion. Vérifiez les types de monnaies et le montant."
        )


async def image(update, context):
    if not context.args:
        await update.message.reply_text("Utilisation: /image description")
        return

    prompt = " ".join(context.args)
    await update.message.reply_text(f"🎨 Création de l'image pour : {prompt}")

    try:
        lien = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {HF_API}"}
        payload = {"inputs": prompt, "options": {"wait_for_model": True}}

        async with aiohttp.ClientSession() as session:
            async with session.post(lien, headers=headers, json=payload) as response:
                print("Status HTTP:", response.status)

                if response.status != 200:
                    error_text = await response.text()
                    print(f"Erreur API: {error_text[:200]}")
                    await update.message.reply_text(
                        "Impossible de générer l'image. "
                        "Vérifiez votre clé API Hugging Face ou réessayez dans quelques instants."
                    )
                    return

                content_type = response.headers.get('Content-Type', '')

                if 'application/json' in content_type:
                    error_data = await response.json()
                    print(f"Erreur JSON: {error_data}")
                    if "estimated_time" in str(error_data):
                        await update.message.reply_text(
                            "⏳ Le modèle est en cours de chargement. "
                            "Veuillez réessayer dans 1-2 minutes."
                        )
                    else:
                        await update.message.reply_text(f"Erreur: {error_data}")
                    return

                image_bytes = await response.read()

                if len(image_bytes) < 100:
                    await update.message.reply_text("L'image générée semble invalide. Réessayez.")
                    return

                image_buffer = BytesIO(image_bytes)
                image_buffer.name = "image.png"

                await update.message.reply_photo(
                    photo=image_buffer,
                    caption=f"🎨 Image générée pour : {prompt}"
                )

    except aiohttp.ClientError as e:
        print(f"Erreur réseau: {e}")
        await update.message.reply_text("Erreur de connexion à l'API Hugging Face.")
    except Exception as e:
        print(f"Erreur de création: {e}")
        await update.message.reply_text(
            "Erreur lors de la création de l'image. Vérifiez le prompt ou réessayez."
        )


async def astro(update, context):
    if not context.args:
        try:
            date_jour = datetime.now().strftime("%Y-%m-%d")
            lien = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API}&date={date_jour}"
            await update.message.reply_text("🔭 Récupération de l'image astronomique du jour...")

            async with aiohttp.ClientSession() as session:
                async with session.get(lien) as response:
                    print("Status HTTP:", response.status)
                    if response.status != 200:
                        await update.message.reply_text("Impossible de récupérer l'image.")
                        return
                    data = await response.json()
                    print("Réponse JSON:", data)

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
                await update.message.reply_text("Type de média inconnu\n")

        except Exception as e:
            print(f"Erreur de récupération APOD: {e}")
            await update.message.reply_text("Erreur de récupération des données astronomiques.")

    else:
        astre = " ".join(context.args).lower()
        await update.message.reply_text("🌕🌌 Travail en cours....")

        lien = f"https://api.le-systeme-solaire.net/rest/bodies/{astre}"

        try:
            await update.message.reply_text(f"🔭 Récupération des informations sur {astre}...")

            async with aiohttp.ClientSession() as session:
                async with session.get(lien) as response:
                    print("Status HTTP:", response.status)
                    if response.status != 200:
                        await update.message.reply_text(f"Impossible de trouver l'astre '{astre}'.")
                        return
                    data = await response.json()
                    print("Réponse JSON:", data)
                    if "englishName" not in data:
                        await update.message.reply_text(f"Aucune information trouvée pour '{astre}'.")
                        return

            nom = data.get("englishName", "Inconnu")
            type_astre = data.get("bodyType", "Inconnu")
            gravite = data.get("gravity", "n.c.")
            masse = data.get("mass", {}).get("massValue", "n.c.")
            masse_exp = data.get("mass", {}).get("massExponent", "")
            rayon = data.get("meanRadius", "n.c.")
            perihelie = data.get("perihelion", "n.c.")
            aphelie = data.get("aphelion", "n.c.")

            texte = (
                f"🌠 *{nom}* ({type_astre})\n\n"
                f"🪶 Gravité : {gravite} m/s²\n"
                f"🌍 Masse : {masse} ×10^{masse_exp} kg\n"
                f"📏 Rayon moyen : {rayon} km\n"
                f"☀️ Périhélie : {perihelie} km\n"
                f"🌑 Aphélie : {aphelie} km\n"
            )
            await update.message.reply_text(texte, parse_mode="Markdown")

        except Exception as e:
            print(f"Erreur de récupération des informations de l'astre: {e}")
            await update.message.reply_text("Erreur de récupération des informations astronomiques.")


# ------------------- Main -------------------

def main():
    app = Application.builder().token(TOKEN).post_init(signal).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("man", man))
    app.add_handler(CommandHandler("addition", addition))
    app.add_handler(CommandHandler("sous", sous))
    app.add_handler(CommandHandler("produit", produit))
    app.add_handler(CommandHandler("div", div))
    app.add_handler(CommandHandler("modulo", modulo))
    app.add_handler(CommandHandler("exp", exp))
    app.add_handler(CommandHandler("bonjour", bonjour))
    app.add_handler(CommandHandler("send", send))
    app.add_handler(CommandHandler("listen", listen))
    app.add_handler(CommandHandler("video", video))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("versetBiblique", versetBiblique))
    # ✅ CORRECTION 4 : Suppression de CommandHandler("signal", signal).
    # "signal" est une fonction de démarrage (post_init), pas une commande utilisateur.
    # Avant : app.add_handler(CommandHandler("signal", signal))  ← SUPPRIMÉ
    app.add_handler(CommandHandler("online", online))
    app.add_handler(CommandHandler("conseil", conseil))
    app.add_handler(CommandHandler("rappel", rappel))
    app.add_handler(CommandHandler("meteo", meteo))
    app.add_handler(CommandHandler("traduire", traduire))
    app.add_handler(CommandHandler("convertir", convertir))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("image", image))
    app.add_handler(CommandHandler("astro", astro))
    # ✅ CORRECTION 5 : Suppression du double handler "bonjour".
    # Le CommandHandler("bonjour") ci-dessus gère déjà /bonjour.
    # Ce MessageHandler gère les messages texte libres (sans commande), c'est correct.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bonjour))

    print("🤖 URANIUM en cours d'exécution....")
    app.run_polling()


if __name__ == "__main__":
    main()
