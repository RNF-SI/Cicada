# Dockerfile pour l'application Angular frontend

# Stage 1: Build de l'application Angular
FROM node:20-alpine AS builder

# Métadonnées
LABEL maintainer="CEN/RNF"
LABEL description="Frontend Angular pour CICADA"

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY package*.json ./

# Installation des dépendances (inclut devDependencies pour le build Angular)
RUN npm ci

# Copie du code source
COPY . .

# Build de l'application en mode production
RUN npm run build:prod

# Stage 2: Serveur Apache pour servir l'application
FROM httpd:2.4-alpine

# Copie de la configuration Apache personnalisée
# Note: mod_rewrite est deja inclus dans httpd:2.4-alpine
COPY docker/apache/httpd.conf /usr/local/apache2/conf/httpd.conf
COPY docker/apache/.htaccess /usr/local/apache2/htdocs/

# Copie des fichiers buildés depuis le stage précédent
COPY --from=builder /app/dist/cicada/browser/ /usr/local/apache2/htdocs/

# Port d'exposition
EXPOSE 80

# Commande par défaut
CMD ["httpd-foreground"]