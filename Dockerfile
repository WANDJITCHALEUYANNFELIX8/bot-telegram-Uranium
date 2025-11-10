# Utilise Python officiel comme image de base
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier uniquement les fichiers nécessaires
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copier tout le code source (sauf ce qui est dans .dockerignore)
COPY . .

# Définir la variable d'environnement pour que python trouve le fichier .env
ENV DOTENV_PATH=/app/.env

# Commande pour démarrer le bot
# Remplace 'bbot.py' par le nom exact de ton fichier principal
CMD ["python3", "bbot.py"]

