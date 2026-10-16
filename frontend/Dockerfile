# Image frontend CICADA : application Angular + documentation (MkDocs) servies par Apache.
#
# ⚠ Contexte de build = RACINE du dépôt (et non ./frontend), parce que l'image
# embarque aussi `documentation/` (site statique servi sous /aide/). Les
# exclusions du contexte sont dans `frontend/Dockerfile.dockerignore` (BuildKit
# lit le .dockerignore placé à côté du Dockerfile, qui prime sur celui de la racine).
#
#   docker build -f frontend/Dockerfile .

# Stage 1: Build de l'application Angular
FROM node:22-alpine AS builder

# Métadonnées
LABEL maintainer="CEN/RNF"
LABEL description="Frontend Angular pour CICADA"

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY frontend/package*.json ./

# Installation des dépendances (inclut devDependencies pour le build Angular)
RUN npm ci

# Copie du code source
COPY frontend/ .

# Build de l'application en mode production
RUN npm run build:prod

# Stage 2: Build de la documentation (MkDocs Material) → /docs/site
FROM python:3.12-alpine AS docs

WORKDIR /docs
COPY documentation/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY documentation/ ./
# --strict : un lien ou une ancre cassés font échouer la construction de l'image.
RUN mkdocs build --strict

# Stage 3: Serveur Apache pour servir l'application et la documentation
FROM httpd:2.4-alpine

LABEL org.opencontainers.image.source="https://github.com/RNF-SI/Cicada"
LABEL org.opencontainers.image.description="Frontend Angular pour CICADA"
LABEL org.opencontainers.image.licenses="GPL-3.0"

# Copie de la configuration Apache personnalisée
# Note: mod_rewrite est deja inclus dans httpd:2.4-alpine
COPY frontend/docker/apache/httpd.conf /usr/local/apache2/conf/httpd.conf
COPY frontend/docker/apache/.htaccess /usr/local/apache2/htdocs/

# Copie des fichiers buildés depuis le stage précédent
COPY --from=builder /app/dist/cicada/browser/ /usr/local/apache2/htdocs/

# Documentation statique, servie sous /aide/ (hors du routage Angular, cf. httpd.conf)
COPY --from=docs /docs/site/ /usr/local/apache2/htdocs/aide/

# Port d'exposition
EXPOSE 80

# Commande par défaut
CMD ["httpd-foreground"]
