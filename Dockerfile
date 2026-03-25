
# ============================================
# Dockerfile — Bot Telegram URANIUM
# ============================================

# Image de base Python légère
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier d'abord requirements.txt pour profiter du cache Docker
COPY requirements.txt .

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Télécharger les données TextBlob (nécessaire pour l'analyse de sentiment)
RUN python -m textblob.download_corpora

# Copier tout le code source dans le conteneur
COPY . .

# ⚠️ Ne pas exposer de port : ce bot tourne en mode polling, pas en serveur web

# Lancer le bot
CMD ["python", "bot_telegram_corrige.py"]
