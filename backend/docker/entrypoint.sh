#!/bin/bash

# Script d'initialisation pour l'application Django
set -e

# Fixer les permissions des volumes montes (executes en root)
if [ "$(id -u)" = "0" ]; then
    chown -R cicada:cicada /app/logs /app/media /app/static 2>/dev/null || true
    exec gosu cicada "$0" "$@"
fi

# Si la commande est celery (worker ou beat), l'exécuter directement sans init.
# Les workers n'ont pas besoin de migrer — seul le conteneur web le fait.
if [ "$#" -gt 0 ] && echo "$1" | grep -q "celery"; then
    echo "=== Exécution Celery : $@ ==="
    exec "$@"
fi

# --- Initialisation (toujours exécutée pour web/gunicorn/runserver) ---

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

# Valeurs par défaut (POSTGRES_HOST/POSTGRES_PORT du docker-compose, sinon DB_HOST/DB_PORT)
export DB_HOST=${DB_HOST:-${POSTGRES_HOST:-db}}
export DB_PORT=${DB_PORT:-${POSTGRES_PORT:-5432}}
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

echo "=== Application des migrations ==="
python manage.py migrate --noinput

echo "=== Import des nomenclatures ==="
python manage.py import_nomenclatures || echo "WARN: import_nomenclatures a échoué (non bloquant)"

echo "=== Import HabRef ==="
python manage.py import_habref || echo "WARN: import_habref a échoué (non bloquant)"

echo "=== Import TaxRef ==="
python manage.py import_taxref ${TAXREF_IMPORT_OPTS:-} || echo "WARN: import_taxref a échoué (non bloquant)"

echo "=== Import INPG ==="
python manage.py import_inpg || echo "WARN: import_inpg a échoué (non bloquant)"

echo "=== Import CAMPanule ==="
python manage.py import_campanule || echo "WARN: import_campanule a échoué (non bloquant)"

echo "=== Import référentiel géographique (régions/départements) ==="
python manage.py import_ref_geo || echo "WARN: import_ref_geo a échoué (non bloquant)"

# Amorçage de l'index de recherche : ne fait rien si l'index est déjà peuplé.
# En régime courant il est maintenu par les signaux (validation d'un plan).
echo "=== Index de recherche ==="
python manage.py rebuild_search_index --if-empty || echo "WARN: rebuild_search_index a échoué (non bloquant)"

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

echo "=== Initialisation terminée ==="

# Lancer la commande passée (gunicorn en prod) ou runserver par défaut
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exec python manage.py runserver 0.0.0.0:8000
fi
