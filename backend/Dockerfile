# Dockerfile pour l'application Django backend
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="CEN/RNF"
LABEL description="Backend Django pour CICADA"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.development

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système pour PostGIS
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création du répertoire pour les médias
RUN mkdir -p /app/media /app/static

# Script d'initialisation
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Port d'exposition
EXPOSE 8000

# Point d'entrée
ENTRYPOINT ["/entrypoint.sh"]

# Commande par défaut
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]