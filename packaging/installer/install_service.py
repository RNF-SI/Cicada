#!/usr/bin/env python3
"""
Service d'installation pour CICADA
"""
import os
import subprocess
import json
import secrets
import requests
from pathlib import Path
from datetime import datetime


def get_tracking_api_url():
    """
    Lit l'URL de l'API de suivi :
    - En dev : depuis variable d'environnement TRACKING_API_URL
    - En production (package) : depuis /etc/cicada/cicada.conf (fixée dans le package)
    """
    import configparser
    
    if os.path.exists('/etc/cicada/cicada.conf'):
        config = configparser.ConfigParser()
        config.read('/etc/cicada/cicada.conf')
        return config.get('CICADA', 'TRACKING_API_URL')
    else:
        return os.environ.get('TRACKING_API_URL', 'https://tracking.cicada.reserves-naturelles.org/api')


class InstallService:
    def __init__(self):
        self.status_file = Path("/var/lib/cicada/install_status.json")
        self.lock_file = Path("/var/lib/cicada/.install_lock")

    def is_installed(self):
        return self.lock_file.exists()

    def get_status(self):
        if self.status_file.exists():
            return json.loads(self.status_file.read_text())
        return {'status': 'not_started', 'steps': []}

    def update_status(self, status, message="", step_name=None, step_status=None):
        """
        Met à jour le statut de l'installation.
        
        Args:
            status: 'not_started', 'in_progress', 'completed', 'failed'
            message: Message général
            step_name: Nom de l'étape (ex: 'db', 'redis', 'web', 'frontend')
            step_status: 'pending', 'running', 'completed', 'failed'
        """
        current_status = self.get_status()
        steps = current_status.get('steps', [])
        
        # Mettre à jour ou ajouter l'étape
        if step_name:
            step_index = next((i for i, s in enumerate(steps) if s['name'] == step_name), -1)
            if step_index >= 0:
                steps[step_index]['status'] = step_status
                steps[step_index]['message'] = message
            else:
                steps.append({
                    'name': step_name,
                    'status': step_status,
                    'message': message
                })
        
        self.status_file.write_text(json.dumps({
            'status': status,
            'message': message,
            'steps': steps,
            'timestamp': datetime.now().isoformat()
        }))

    def run_installation(self, data):
        try:
            self.update_status('in_progress', 'Validation des données...')

            # 1. Valider les données
            errors = self.validate_data(data)
            if errors:
                return {'success': False, 'errors': errors}

            # 2. Générer les secrets
            self.update_status('in_progress', 'Génération des secrets...')
            secrets_data = self.generate_secrets(data)

            # 3. Créer le fichier .env
            self.update_status('in_progress', 'Configuration de l\'environnement...')
            self.create_env_file(data, secrets_data)
            
            # 3.5. Générer le docker-compose.yml adapté
            self.update_status('in_progress', 'Configuration de Docker Compose...')
            self.generate_docker_compose(data)

            # 4. Lancer Docker Compose
            self.update_status('in_progress', 'Démarrage des conteneurs Docker...')
            self.start_docker()

            # 5. Créer le superutilisateur
            self.update_status('in_progress', 'Création du compte administrateur...')
            self.create_superuser(data)

            # 6. Enregistrer l'instance (non bloquant - ne doit jamais bloquer l'installation)
            self.update_status('in_progress', 'Enregistrement de l\'instance (optionnel)...')
            try:
                self.register_instance(data)
            except Exception as e:
                # Ne jamais bloquer l'installation si l'API est indisponible
                # L'enregistrement pourra se faire plus tard via le heartbeat
                pass

            # 7. Finaliser
            self.update_status('completed', 'Installation terminée !')
            self.lock_file.touch()

            return {
                'success': True,
                'redirect_url': f"http://{data['domain']}:{data.get('frontend_port', 4200)}"
            }

        except Exception as e:
            self.update_status('failed', str(e))
            return {'success': False, 'error': str(e)}

    def validate_data(self, data):
        errors = []
        required = ['admin_email', 'admin_password', 'admin_nom',
                    'admin_prenom', 'domain', 'db_password']
        for field in required:
            if not data.get(field):
                errors.append(f"Le champ {field} est requis")
        if data.get('smtp_enabled'):
            smtp_required = ['smtp_host', 'smtp_port', 'default_from_email']
            for field in smtp_required:
                if not data.get(field):
                    errors.append(f"Le champ {field} est requis lorsque SMTP est activé.")
            if data.get('smtp_use_auth'):
                if not data.get('smtp_user'):
                    errors.append("Le champ smtp_user est requis lorsque l'authentification SMTP est activée.")
                if not data.get('smtp_password'):
                    errors.append("Le champ smtp_password est requis lorsque l'authentification SMTP est activée.")
        return errors

    def generate_secrets(self, data):
        return {
            'secret_key': secrets.token_urlsafe(50),
            'db_password': data.get('db_password') or secrets.token_urlsafe(32),
            'redis_password': data.get('redis_password') or secrets.token_urlsafe(32),
        }

    def create_env_file(self, data, secrets_data):
        token = Path("/etc/cicada/instance_token").read_text().strip()
        tracking_api_url = get_tracking_api_url()
        
        # Utiliser les paramètres fournis par l'utilisateur
        db_name = data.get('db_name', 'cicada')
        db_user = data.get('db_user', 'cicada_user')
        db_password = secrets_data.get('db_password', secrets_data.get('db_password'))
        db_host = data.get('db_host', 'db')
        db_port = data.get('db_port', 5432)
        db_type = data.get('db_type', 'docker')
        smtp_enabled = data.get('smtp_enabled') in (True, 'true', '1')
        smtp_use_auth = data.get('smtp_use_auth') in (True, 'true', '1')
        smtp_use_tls = data.get('smtp_use_tls') in (True, 'true', '1')

        env_content = f"""SECRET_KEY={secrets_data['secret_key']}
DEBUG=False
ALLOWED_HOSTS={data['domain']}

POSTGRES_DB={db_name}
POSTGRES_USER={db_user}
POSTGRES_PASSWORD={db_password}
POSTGRES_HOST={db_host}
POSTGRES_PORT={db_port}
DB_TYPE={db_type}

REDIS_HOST={data.get('redis_host', 'redis')}
REDIS_PORT={data.get('redis_port', 6379)}
REDIS_PASSWORD={secrets_data['redis_password']}

FRONTEND_PORT={data.get('frontend_port', 4200)}
DJANGO_PORT={data.get('backend_port', 8000)}

EMAIL_BACKEND={'django.core.mail.backends.smtp.EmailBackend' if smtp_enabled else 'django.core.mail.backends.console.EmailBackend'}
EMAIL_HOST={data.get('smtp_host', '').strip() if smtp_enabled else ''}
EMAIL_PORT={data.get('smtp_port', 587) if smtp_enabled else 587}
EMAIL_USE_TLS={'true' if smtp_enabled and smtp_use_tls else 'false'}
EMAIL_HOST_USER={data.get('smtp_user', '').strip() if smtp_enabled and smtp_use_auth else ''}
EMAIL_HOST_PASSWORD={data.get('smtp_password', '').strip() if smtp_enabled and smtp_use_auth else ''}
DEFAULT_FROM_EMAIL={data.get('default_from_email', 'noreply@cicada.fr').strip() if smtp_enabled else 'noreply@cicada.fr'}

INSTANCE_TOKEN={token}
TRACKING_API_URL={tracking_api_url}
"""
        Path("/var/lib/cicada/.env").write_text(env_content)

    def generate_docker_compose(self, data):
        """
        Génère un docker-compose.yml adapté selon le type de base de données choisi.
        Si db_type=existing, on n'utilise pas le profile with-db pour ne pas démarrer le conteneur db.
        """
        db_type = data.get('db_type', 'docker')
        
        # Le docker-compose.yml de base utilise déjà des profiles
        # On n'a qu'à s'assurer d'utiliser le bon profile lors du démarrage
        # Pas besoin de modifier le fichier, on utilisera --profile avec-db ou non
        
        # Sauvegarder le type de DB pour le démarrage
        Path("/var/lib/cicada/db_type").write_text(db_type)

    def start_docker(self):
        # Vérifier que Docker est disponible
        docker_cmd = self._find_docker_command()
        if not docker_cmd:
            raise Exception("Docker n'est pas installé ou n'est pas dans le PATH. Veuillez installer Docker avant de continuer.")
        
        # Vérifier que docker compose est disponible
        try:
            result = subprocess.run(
                [docker_cmd, 'compose', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise Exception("Docker Compose n'est pas disponible. Veuillez installer docker-compose-plugin.")
        except FileNotFoundError:
            raise Exception("Docker Compose n'est pas disponible. Veuillez installer docker-compose-plugin.")
        
        # Lire le type de DB depuis le fichier .env
        env_file = '/var/lib/cicada/.env'
        db_type = 'docker'  # Par défaut
        if Path(env_file).exists():
            env_content = Path(env_file).read_text()
            for line in env_content.splitlines():
                if line.startswith('DB_TYPE='):
                    db_type = line.split('=', 1)[1].strip()
                    break
        
        # Initialiser les étapes selon le type de DB
        if db_type == 'docker':
            self.update_status('in_progress', 'Démarrage des conteneurs...', 'db', 'running')
        else:
            self.update_status('in_progress', 'Utilisation d\'une instance PostgreSQL existante', 'db', 'completed')
        self.update_status('in_progress', 'Démarrage des conteneurs...', 'redis', 'pending')
        self.update_status('in_progress', 'Démarrage des conteneurs...', 'web', 'pending')
        self.update_status('in_progress', 'Démarrage des conteneurs...', 'frontend', 'pending')
        
        # Vérifier que le backend est présent avant de lancer docker compose
        backend_path = Path("/usr/share/cicada/backend/manage.py")
        if not backend_path.exists():
            raise Exception(f"Le backend n'est pas présent à {backend_path}. Vérifiez l'installation du package.")
        
        # Vérifier que le répertoire backend existe et contient les fichiers nécessaires
        backend_dir = Path("/usr/share/cicada/backend")
        if not backend_dir.exists():
            raise Exception(f"Le répertoire backend n'existe pas: {backend_dir}")
        
        # Lister les fichiers pour diagnostic
        list_result = subprocess.run(
            ['ls', '-la', '/usr/share/cicada/backend/'],
            capture_output=True,
            text=True
        )
        if list_result.returncode == 0:
            self.update_status('in_progress', f'Backend trouvé: {list_result.stdout[:200]}')
        
        # Vérifier que le volume sera bien monté en testant l'accès au répertoire
        # Dans Docker-in-Docker, le volume bind mount doit fonctionner depuis le conteneur hôte
        test_volume = subprocess.run(
            ['test', '-d', '/usr/share/cicada/backend'],
            capture_output=True
        )
        if test_volume.returncode != 0:
            raise Exception("Le répertoire /usr/share/cicada/backend n'est pas accessible. Vérifiez l'installation du package.")
        
        # Construire l'image web (sans --no-cache pour réutiliser les couches si possible)
        self.update_status('in_progress', 'Construction de l\'image Docker...', 'web', 'running')
        build_cmd = [docker_cmd, 'compose', '-f', '/usr/share/cicada/docker-compose.yml',
                    '--env-file', env_file, 'build', 'web']
        build_result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max pour le build
        )
        if build_result.returncode != 0:
            error_msg = build_result.stderr or build_result.stdout
            # Vérifier si c'est un problème de réseau
            if 'timeout' in error_msg.lower() or 'failed to resolve' in error_msg.lower() or 'dial tcp' in error_msg.lower():
                self.update_status('in_progress', 'Erreur réseau lors du téléchargement de l\'image de base. Vérifiez votre connexion Internet.', 'web', 'failed')
                raise Exception(f"Erreur réseau lors de la construction de l'image. Assurez-vous que Docker peut accéder à Docker Hub.\n{error_msg}")
            else:
                self.update_status('in_progress', f'Erreur lors de la construction: {error_msg}', 'web', 'failed')
                raise Exception(f"Erreur lors de la construction de l'image: {error_msg}")
        
        # Vérifier que le build a bien copié le code (le volume montera par-dessus)
        # Le volume bind mount devrait monter /usr/share/cicada/backend depuis l'hôte vers /app dans le conteneur
        
        # Lancer docker compose avec ou sans le service db
        self.update_status('in_progress', 'Lancement de Docker Compose...')
        compose_cmd = [docker_cmd, 'compose', '-f', '/usr/share/cicada/docker-compose.yml',
                      '--env-file', env_file]
        
        # Si DB existante, ne pas utiliser le profile with-db (db ne sera pas démarré)
        # Si DB docker, utiliser le profile with-db pour démarrer db
        if db_type == 'docker':
            compose_cmd.extend(['--profile', 'with-db'])
        
        compose_cmd.extend(['up', '-d'])
        
        result = subprocess.run(
            compose_cmd,
            check=True, capture_output=True, text=True
        )
        
        # Attendre un peu pour que les conteneurs commencent à démarrer
        import time
        time.sleep(5)
        
        # Attendre que les services soient prêts et vérifier qu'ils sont démarrés
        import time
        docker_compose_file = '/usr/share/cicada/docker-compose.yml'
        env_file = '/var/lib/cicada/.env'
        
        # Attendre que les conteneurs soient démarrés
        max_wait = 300  # 5 minutes max (le build peut prendre du temps)
        wait_interval = 5
        elapsed = 0
        db_running = False
        redis_running = False
        web_running = False
        frontend_running = False
        
        while elapsed < max_wait:
            # Vérifier l'état de tous les conteneurs
            ps_result = subprocess.run(
                [docker_cmd, 'compose', '-f', docker_compose_file,
                 '--env-file', env_file, 'ps'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if ps_result.returncode == 0:
                ps_output = ps_result.stdout.lower()
                
                # Vérifier la base de données (seulement si DB_TYPE = docker)
                if db_type == 'docker':
                    if not db_running and 'cicada_db' in ps_output and 'running' in ps_output and 'healthy' in ps_output:
                        db_running = True
                        self.update_status('in_progress', 'Base de données démarrée', 'db', 'completed')
                else:
                    # Pour DB existante, on considère qu'elle est prête (l'utilisateur doit l'avoir configurée)
                    db_running = True
                
                # Vérifier Redis
                if not redis_running and 'cicada_redis' in ps_output and 'running' in ps_output and 'healthy' in ps_output:
                    redis_running = True
                    self.update_status('in_progress', 'Redis démarré', 'redis', 'completed')
                
                # Vérifier le conteneur web
                if not web_running:
                    if 'cicada_web' in ps_output:
                        if 'running' in ps_output:
                            web_running = True
                            self.update_status('in_progress', 'Conteneur web démarré, attente de Django...', 'web', 'completed')
                            # Attendre encore un peu pour que Django soit prêt
                            time.sleep(20)
                        elif 'exited' in ps_output:
                            self.update_status('in_progress', 'Conteneur web en cours de démarrage...', 'web', 'running')
                    else:
                        self.update_status('in_progress', 'Construction du conteneur web...', 'web', 'running')
                
                # Vérifier le frontend (optionnel, peut échouer sans bloquer)
                if not frontend_running and 'cicada_frontend' in ps_output:
                    if 'running' in ps_output:
                        frontend_running = True
                        self.update_status('in_progress', 'Frontend démarré', 'frontend', 'completed')
                    elif 'exited' in ps_output:
                        self.update_status('in_progress', 'Frontend en cours de démarrage...', 'frontend', 'running')
            
            # Si tous les conteneurs critiques sont prêts, on peut continuer
            # Pour DB existante, db_running est toujours True
            if db_running and redis_running and web_running:
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        if not web_running:
            # Récupérer les logs pour diagnostiquer le problème
            logs_result = subprocess.run(
                [docker_cmd, 'compose', '-f', docker_compose_file,
                 '--env-file', env_file, 'logs', '--tail', '50'],
                capture_output=True,
                text=True,
                timeout=10
            )
            logs_output = logs_result.stdout if logs_result.returncode == 0 else "Impossible de récupérer les logs"
            
            # Vérifier l'état des conteneurs
            ps_result = subprocess.run(
                [docker_cmd, 'compose', '-f', docker_compose_file,
                 '--env-file', env_file, 'ps', '-a'],
                capture_output=True,
                text=True,
                timeout=10
            )
            ps_output = ps_result.stdout if ps_result.returncode == 0 else "Impossible de récupérer l'état"
            
            error_msg = (
                f"Le conteneur 'web' n'est pas en cours d'exécution après {elapsed} secondes.\n\n"
                f"État des conteneurs:\n{ps_output}\n\n"
                f"Derniers logs:\n{logs_output}"
            )
            raise Exception(error_msg)

    def create_superuser(self, data):
        docker_cmd = self._find_docker_command()
        if not docker_cmd:
            raise Exception("Docker n'est pas disponible")
        
        docker_compose_file = '/usr/share/cicada/docker-compose.yml'
        env_file = '/var/lib/cicada/.env'
        
        # Vérifier d'abord que le conteneur web est en cours d'exécution
        ps_result = subprocess.run(
            [docker_cmd, 'compose', '-f', docker_compose_file,
             '--env-file', env_file, 'ps', 'web'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if ps_result.returncode != 0 or 'running' not in ps_result.stdout.lower():
            # Essayer de voir l'état de tous les conteneurs
            all_ps = subprocess.run(
                [docker_cmd, 'compose', '-f', docker_compose_file,
                 '--env-file', env_file, 'ps', '-a'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Récupérer les logs du conteneur web
            logs_result = subprocess.run(
                [docker_cmd, 'compose', '-f', docker_compose_file,
                 '--env-file', env_file, 'logs', 'web', '--tail', '30'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            containers_state = all_ps.stdout if all_ps.returncode == 0 else "Impossible de récupérer l'état"
            logs_output = logs_result.stdout if logs_result.returncode == 0 else "Impossible de récupérer les logs"

            error_msg = (
                "Le conteneur 'web' n'est pas en cours d'exécution.\n\n"
                f"État des conteneurs:\n{containers_state}\n\n"
                f"Derniers logs du conteneur web:\n{logs_output}"
            )
            raise Exception(error_msg)
        
        # Échapper les apostrophes et guillemets dans les données pour éviter les erreurs de shell
        admin_email = data['admin_email'].replace("'", "\\'").replace('"', '\\"')
        admin_nom = data['admin_nom'].replace("'", "\\'").replace('"', '\\"')
        admin_prenom = data['admin_prenom'].replace("'", "\\'").replace('"', '\\"')
        admin_password = data['admin_password'].replace("'", "\\'").replace('"', '\\"')
        
        # Utiliser create_superuser avec les bons noms de champs (nom_role, prenom_role)
        python_script = f"""
from apps.users.models import Role
try:
    # Vérifier si l'utilisateur existe déjà
    existing = Role.objects.filter(email='{admin_email}').first()
    if existing:
        print(f'Utilisateur {{existing.email}} existe déjà')
        existing.delete()
    
    # Créer le superutilisateur avec create_superuser
    user = Role.objects.create_superuser(
        email='{admin_email}',
        password='{admin_password}',
        nom_role='{admin_nom}',
        prenom_role='{admin_prenom}',
        active=True
    )
    print(f'Superuser créé avec succès: {{user.email}}')
except Exception as e:
    import traceback
    print(f'ERREUR lors de la création du superuser: {{e}}')
    traceback.print_exc()
    raise
"""
        
        result = subprocess.run(
            [docker_cmd, 'compose', '-f', docker_compose_file,
             '--env-file', env_file,
             'exec', '-T', 'web', 'python', 'manage.py', 'shell', '-c', python_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            error_msg = f"Erreur lors de la création du superuser:\n{result.stderr}\n{result.stdout}"
            raise Exception(error_msg)
        
        # Vérifier que la création a réussi dans la sortie
        if 'Superuser créé avec succès' not in result.stdout:
            raise Exception(f"La création du superuser semble avoir échoué. Sortie: {result.stdout}\nErreurs: {result.stderr}")

    def register_instance(self, data):
        """
        Enregistre l'instance auprès de l'API de suivi (non bloquant)
        
        Cette méthode ne doit JAMAIS lever d'exception qui bloquerait l'installation.
        Si l'API est indisponible, l'enregistrement sera tenté plus tard via le heartbeat.
        """
        try:
            token = Path("/etc/cicada/instance_token").read_text().strip()
            version = self.get_version()

            payload = {
                'token': token,
                'version': version,
                'rgpd_consent': data.get('rgpd_consent', False),
            }

            # Ajouter les données nominatives si consentement
            if data.get('rgpd_consent'):
                payload.update({
                    'admin_name': f"{data.get('admin_prenom', '')} {data.get('admin_nom', '')}",
                    'admin_email': data.get('contact_email') or data.get('admin_email'),
                    'structure_name': data.get('structure_name'),
                })

            tracking_url = get_tracking_api_url()
            
            # Timeout court pour ne pas bloquer trop longtemps
            response = requests.post(
                f"{tracking_url}/instances/register/",
                json=payload,
                headers={'X-Instance-Token': token},
                timeout=10  # Timeout réduit à 10 secondes
            )
            response.raise_for_status()
            
            # Enregistrement réussi
            registration_pending = Path("/var/lib/cicada/registration_pending")
            if registration_pending.exists():
                registration_pending.unlink()  # Supprimer le fichier d'erreur si présent

        except requests.exceptions.Timeout:
            # Timeout : l'API ne répond pas assez vite, on continue
            Path("/var/lib/cicada/registration_pending").write_text(
                "Timeout: L'API de suivi n'a pas répondu dans les délais. "
                "L'enregistrement sera tenté plus tard via le heartbeat quotidien."
            )
        except requests.exceptions.ConnectionError:
            # Pas de connexion : l'API est probablement indisponible
            Path("/var/lib/cicada/registration_pending").write_text(
                "ConnectionError: Impossible de contacter l'API de suivi. "
                "L'enregistrement sera tenté plus tard via le heartbeat quotidien."
            )
        except requests.exceptions.RequestException as e:
            # Autre erreur HTTP
            Path("/var/lib/cicada/registration_pending").write_text(
                f"Erreur HTTP: {str(e)}. "
                "L'enregistrement sera tenté plus tard via le heartbeat quotidien."
            )
        except Exception as e:
            # Toute autre erreur (fichier manquant, etc.)
            Path("/var/lib/cicada/registration_pending").write_text(
                f"Erreur: {str(e)}. "
                "L'enregistrement sera tenté plus tard via le heartbeat quotidien."
            )
        
        # Ne jamais lever d'exception - l'installation doit toujours continuer

    def _find_docker_command(self):
        """Trouve la commande docker dans le système"""
        # Chercher dans les chemins standards
        docker_paths = ['/usr/bin/docker', '/usr/local/bin/docker', 'docker']
        
        for docker_path in docker_paths:
            try:
                result = subprocess.run(
                    [docker_path, '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return docker_path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        # Essayer avec which/whereis
        try:
            result = subprocess.run(
                ['which', 'docker'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return None

    def get_version(self):
        config_file = Path("/etc/cicada/cicada.conf")
        if config_file.exists():
            for line in config_file.read_text().splitlines():
                if line.startswith('VERSION='):
                    return line.split('=', 1)[1].strip()
        return "unknown"
