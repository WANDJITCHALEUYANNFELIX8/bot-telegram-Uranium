# Choix de l'image Python
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier le code et le fichier .env
COPY . /app

# Installer les dépendances
RUN pip install --no-cache-dir --upgrade pip \ && pip install --no-cache-dir -r requirements.txt

COPY .env

# Commande pour lancer le bot
CMD ["python3", "bbot.py"]

