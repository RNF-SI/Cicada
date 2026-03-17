#!/bin/bash

# Script d'initialisation pour l'application Django
set -e

# Fixer les permissions des volumes montes (executes en root)
if [ "$(id -u)" = "0" ]; then
    chown -R cicada:cicada /app/logs /app/media /app/static 2>/dev/null || true
    exec gosu cicada "$0" "$@"
fi

# Si une commande custom est passée (via docker-compose command:),
# on l'exécute directement sans l'initialisation complète.
# L'initialisation (migrate, import, etc.) est gérée par la command: elle-même.
if [ "$#" -gt 0 ]; then
    echo "=== Exécution de la commande : $@ ==="
    exec "$@"
fi

# --- Initialisation complète (CMD par défaut du Dockerfile) ---

echo "=== Initialisation de l'application Django ==="

# Fonction pour attendre que la base de données soit disponible
wait_for_db() {
    echo "En attente de la base de données..."
    while ! nc -z $DB_HOST $DB_PORT; do
        echo "PostgreSQL n'est pas encore disponible - attente..."
        sleep 2
    done
    echo "PostgreSQL est disponible !"
}

# Fonction pour attendre que Redis soit disponible
wait_for_redis() {
    echo "En attente de Redis..."
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
        echo "Redis n'est pas encore disponible - attente..."
        sleep 2
    done
    echo "Redis est disponible !"
}

# Extraction des paramètres de connexion depuis DATABASE_URL et REDIS_URL
if [ -n "$DATABASE_URL" ]; then
    export DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    export DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
fi

if [ -n "$REDIS_URL" ]; then
    export REDIS_HOST=$(echo $REDIS_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    export REDIS_PORT=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
fi

# Valeurs par défaut
export DB_HOST=${DB_HOST:-db}
export DB_PORT=${DB_PORT:-5432}
export REDIS_HOST=${REDIS_HOST:-redis}
export REDIS_PORT=${REDIS_PORT:-6379}

# Vérifier que netcat est disponible (installé dans le Dockerfile)
if ! command -v nc &> /dev/null; then
    echo "ERREUR: netcat n'est pas installé. Vérifiez le Dockerfile."
    exit 1
fi

# Attendre les services externes
wait_for_db
wait_for_redis

echo "=== Vérification des migrations ==="
python manage.py showmigrations

echo "=== Application des migrations ==="
python manage.py migrate --noinput

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput --clear

echo "=== Vérification du système Django ==="
python manage.py check

# Création d'un superutilisateur en développement si les variables sont définies
if [ "$DEBUG" = "True" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "=== Création du superutilisateur de développement ==="
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser(
        email='$DJANGO_SUPERUSER_EMAIL',
        password='$DJANGO_SUPERUSER_PASSWORD',
        nom_role='Admin',
        prenom_role='Super'
    )
    print('Superutilisateur créé avec succès')
else:
    print('Superutilisateur déjà existant')
"
fi

# Chargement des données de test/référence en développement
if [ "$DEBUG" = "True" ] && [ "$LOAD_FIXTURES" = "True" ]; then
    echo "=== Chargement des données de référence ==="
    # Les fixtures seront ajoutées plus tard
    # python manage.py loaddata fixtures/dev_data.json
fi

echo "=== Initialisation terminée ==="

# Commande par défaut : lancer le serveur
exec python manage.py runserver 0.0.0.0:8000
