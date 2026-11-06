#!/usr/bin/env python3
"""Mise à jour, sauvegarde et restauration d'une instance CICADA (#796).

Utilisé par les commandes du serveur, en root :

    cicada-update   état, mise à jour, nouvelle tentative, retour arrière, reprise
    cicada-backup   sauvegarde (base, fichiers déposés, configuration)
    cicada-restore  restauration d'une sauvegarde

et par le paquet lui-même : le postinst lance `cicada-update deploy`, si bien
que le bouton « Mettre à jour », `apt install` et `dpkg -i` suivent le même
déroulé :

    contrôles (espace disque) → téléchargement des images → arrêt de l'application
    → sauvegarde vérifiée → bascule de version → démarrage et vérification
    → en cas d'échec : retour à la version précédente, avec la base d'avant.

Tant que l'application n'a pas été arrêtée, un échec ne change rien. Chaque
étape est notée dans /var/lib/cicada/maintenance/tentative.json : une
mise à jour interrompue (serveur redémarré) est reprise au démarrage suivant
(cicada-reprise.service) à partir de la sauvegarde d'origine.

La base est sauvegardée et restaurée par `cicada-db`, outil de l'image backend
lancé dans un conteneur ponctuel du service `web` : c'est donc la base que
l'application utilise réellement (Docker ou PostgreSQL existant).
"""
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Résultats d'une tentative, et code de sortie des commandes
REUSSIE = 'reussie'
A_JOUR = 'a_jour'
ANNULEE = 'annulee'            # rien n'a changé (ou application relancée telle quelle)
RETOUR_FAIT = 'echec_retour_fait'
SANS_RETOUR = 'echec_sans_retour'
EN_COURS = 'en_cours'
CODES = {REUSSIE: 0, A_JOUR: 0, ANNULEE: 10, RETOUR_FAIT: 11, SANS_RETOUR: 12}

WEB = 'cicada_prod_web'
OUTILS = 'cicada_prod_outils'
DEPENDANTS = {
    'frontend': 'cicada_prod_frontend',
    'celery-worker': 'cicada_prod_celery_worker',
    'celery-beat': 'cicada_prod_celery_beat',
}
TRAEFIK = ('traefik', 'cicada_traefik')
# Ordre d'arrêt : ce qui écrit dans la base, puis web
APPLICATION = ['frontend', 'celery-beat', 'celery-worker', 'web']
IMAGES_CICADA = ('ghcr.io/rnf-si/cicada-backend', 'ghcr.io/rnf-si/cicada-frontend')

COMMANDE_REPRISE = 'sudo cicada-update rollback'


class ErreurMaintenance(Exception):
    """Échec expliqué, affiché tel quel à l'administrateur."""


class Chemins:
    def __init__(self, racine='/'):
        r = Path(racine)
        self.env = r / 'var/lib/cicada/.env'
        self.compose = r / 'usr/share/cicada'
        self.version = r / 'usr/share/cicada/VERSION'
        self.etat = r / 'var/lib/cicada/maintenance'
        self.echanges = r / 'var/lib/cicada/updates'
        self.journaux = r / 'var/log/cicada'
        self.sauvegardes_defaut = r / 'var/backups/cicada'


def cle_version(version):
    try:
        return tuple(int(p) for p in str(version).split('.'))
    except (TypeError, ValueError):
        return ()


def horodatage():
    return datetime.now().astimezone().isoformat(timespec='seconds')


class Instance:
    """Une instance CICADA installée par le paquet. Les appels au système
    (commandes, horloge, espace disque) sont injectables pour les tests."""

    def __init__(self, chemins=None, executer=subprocess.run, dormir=time.sleep, horloge=time.time,
                 espace_libre=None, sortie=sys.stderr):
        self.c = chemins or Chemins()
        self.executer = executer
        self.dormir = dormir
        self.horloge = horloge
        self.espace_libre = espace_libre or (lambda chemin: shutil.disk_usage(chemin).free)
        self.sortie = sortie
        self._projet = None

    # ------------------------------------------------------------------
    # Journal, configuration
    # ------------------------------------------------------------------

    def dire(self, message):
        print(message, file=self.sortie, flush=True)
        try:
            self.c.journaux.mkdir(parents=True, exist_ok=True)
            with open(self.c.journaux / 'updater.log', 'a') as f:
                f.write(f"{horodatage()} {message}\n")
        except OSError:
            pass

    def env(self):
        valeurs = {}
        try:
            for ligne in self.c.env.read_text().splitlines():
                if '=' in ligne and not ligne.lstrip().startswith('#'):
                    cle, valeur = ligne.split('=', 1)
                    valeurs[cle.strip()] = valeur.strip()
        except FileNotFoundError:
            pass
        return valeurs

    def reglage(self, cle, defaut):
        valeur = self.env().get(cle, '')
        if not valeur:
            return defaut
        try:
            return type(defaut)(valeur)
        except ValueError:
            return defaut

    def installee(self):
        return self.c.env.exists()

    def version_paquet(self):
        try:
            return self.c.version.read_text().strip()
        except FileNotFoundError:
            return ''

    def version_en_service(self):
        return self.env().get('CICADA_VERSION', '')

    def ecrire_version(self, version):
        """CICADA_VERSION dans le .env (secrets : root seul, mode conservé)."""
        lignes = self.c.env.read_text().splitlines()
        for i, ligne in enumerate(lignes):
            if ligne.startswith('CICADA_VERSION='):
                lignes[i] = f'CICADA_VERSION={version}'
                break
        else:
            lignes.append(f'CICADA_VERSION={version}')
        tmp = self.c.env.with_name('.env.maj')
        tmp.write_text('\n'.join(lignes) + '\n')
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.c.env)

    def dossier_sauvegardes(self):
        return Path(self.env().get('CICADA_SAUVEGARDE_DOSSIER') or self.c.sauvegardes_defaut)

    def traefik(self):
        return self.env().get('TRAEFIK_ENABLED', '').lower() in ('true', '1', 'yes')

    def base_docker(self):
        return (self.env().get('DB_TYPE') or 'docker') == 'docker'

    # ------------------------------------------------------------------
    # Commandes
    # ------------------------------------------------------------------

    def run(self, cmd, env=None, timeout=None):
        try:
            return self.executer(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, 124, '', f'délai dépassé ({timeout} s)')
        except FileNotFoundError as e:
            return subprocess.CompletedProcess(cmd, 127, '', str(e))

    def projet(self):
        """Projet Compose de l'instance. Le déduire du dossier des fichiers
        donnerait un autre projet pour une copie de ces fichiers : d'autres
        volumes, donc une base vide."""
        if self._projet is None:
            r = self.run(['docker', 'inspect', '-f', '{{index .Config.Labels "com.docker.compose.project"}}', WEB])
            self._projet = (r.stdout.strip() if r.returncode == 0 else '') or 'cicada'
        return self._projet

    def dossier_compose(self, version):
        """Fichiers compose de la version demandée : copie faite par le preinst
        avant que le paquet ne les remplace, sinon ceux du paquet installé."""
        copie = self.c.etat / 'compose' / str(version)
        return copie if version and copie.is_dir() else self.c.compose

    def fichiers_compose(self, dossier):
        noms = ['docker-compose.yml']
        if self.base_docker():
            noms.append('docker-compose.db.yml')
        noms.append('docker-compose.traefik.yml' if self.traefik() else 'docker-compose.frontend-ports.yml')
        args = []
        for nom in noms:
            chemin = Path(dossier) / nom
            if not chemin.exists():
                chemin = self.c.compose / nom
            args += ['-f', str(chemin)]
        return args

    def compose(self, *args, version=None, fichiers_de=None, timeout=900):
        """docker compose de l'instance. version : image à utiliser à la place
        de CICADA_VERSION (l'environnement prime sur --env-file). fichiers_de :
        version dont prendre les fichiers compose."""
        dossier = self.dossier_compose(fichiers_de) if fichiers_de else self.c.compose
        cmd = (['docker', 'compose', '-p', self.projet()] + self.fichiers_compose(dossier)
               + ['--env-file', str(self.c.env)] + list(args))
        env = dict(os.environ)
        env.pop('CICADA_VERSION', None)
        if version:
            env['CICADA_VERSION'] = version
        return self.run(cmd, env=env, timeout=timeout)

    def etat_conteneur(self, nom):
        """(statut, santé, redémarrages) ; statut « absent » s'il n'existe pas."""
        r = self.run(['docker', 'inspect', '-f',
                      '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}|{{.RestartCount}}', nom])
        if r.returncode != 0:
            return 'absent', '', 0
        statut, sante, redemarrages = (r.stdout.strip().split('|') + ['', '', '0'])[:3]
        try:
            return statut, sante, int(redemarrages or 0)
        except ValueError:
            return statut, sante, 0

    @staticmethod
    def resume(r, n=600):
        return ((r.stderr or '') + '\n' + (r.stdout or '')).strip()[-n:]

    # ------------------------------------------------------------------
    # État de la tentative (survit à un redémarrage du serveur)
    # ------------------------------------------------------------------

    def _fichier_tentative(self):
        return self.c.etat / 'tentative.json'

    def tentative(self):
        try:
            return json.loads(self._fichier_tentative().read_text())
        except (FileNotFoundError, ValueError):
            return None

    def noter(self, t, **champs):
        t.update(champs)
        self.c.etat.mkdir(parents=True, exist_ok=True)
        os.chmod(self.c.etat, 0o700)
        tmp = self._fichier_tentative().with_suffix('.partiel')
        tmp.write_text(json.dumps(t, indent=1, ensure_ascii=False))
        os.replace(tmp, self._fichier_tentative())

    def ecrire_resultat(self, t):
        """Résultat lu par la page Administration › Mise à jour (dossier
        d'échange monté dans le conteneur web)."""
        try:
            self.c.echanges.mkdir(parents=True, exist_ok=True)
            resultat = {
                'success': t['statut'] in (REUSSIE, A_JOUR),
                'version': t['cible'],
                'timestamp': t.get('fin') or horodatage(),
                'error': t.get('cause') or None,
                'statut': t['statut'],
                'depart': t.get('depart'),
                'cible': t['cible'],
                'retour_arriere': t['statut'] == RETOUR_FAIT,
                'sauvegarde': Path(t['sauvegarde']).name if t.get('sauvegarde') else None,
                'journal': t.get('journal'),
                'commande': COMMANDE_REPRISE if t['statut'] == SANS_RETOUR else None,
                'avertissement': t.get('avertissement') or None,
            }
            chemin = self.c.echanges / 'update_result.json'
            tmp = chemin.with_suffix('.partiel')
            tmp.write_text(json.dumps(resultat, ensure_ascii=False))
            os.chmod(tmp, 0o644)
            os.replace(tmp, chemin)
        except OSError as e:
            self.dire(f"  ! résultat non écrit pour l'application : {e}")

    def verrou(self):
        self.c.etat.mkdir(parents=True, exist_ok=True)
        os.chmod(self.c.etat, 0o700)
        f = open(self.c.etat / 'verrou', 'w')
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            f.close()
            raise ErreurMaintenance("Une mise à jour, une sauvegarde ou une restauration est déjà en cours "
                                    "(journal : /var/log/cicada/updater.log)")
        return f

    # ------------------------------------------------------------------
    # Sauvegardes
    # ------------------------------------------------------------------

    def outil_base(self, action, dossier, fichiers, version):
        """cicada-db dans un conteneur ponctuel du service web."""
        image = f'{IMAGES_CICADA[0]}:{version}'
        if not self.image_presente(image):
            r = self.run(['docker', 'pull', '-q', image], timeout=1800)
            if r.returncode != 0:
                raise ErreurMaintenance(f"Image de l'outil de sauvegarde ({image}) indisponible : {self.resume(r, 300)}")
        self.run(['docker', 'rm', '-f', OUTILS])
        args = ['run', '--rm', '--no-deps', '-T', '--name', OUTILS, '-l', 'traefik.enable=false',
                '-v', f'{dossier}:/sauvegarde', '--entrypoint', 'cicada-db', 'web', action, '/sauvegarde']
        if fichiers:
            args += ['--fichiers', '/app/media']
        r = self.compose(*args, version=version, timeout=4 * 3600)
        resultat = {}
        for ligne in reversed((r.stdout or '').strip().splitlines()):
            try:
                resultat = json.loads(ligne)
                break
            except ValueError:
                continue
        if r.returncode != 0 or not resultat.get('ok'):
            raise ErreurMaintenance(resultat.get('erreur') or self.resume(r) or f'code {r.returncode}')
        return resultat

    def demarrer_base(self):
        """Base en conteneur : la démarrer si besoin (sauvegarde application arrêtée)."""
        if not self.base_docker():
            return
        if self.etat_conteneur('cicada_prod_db')[1] == 'healthy':
            return
        self.compose('up', '-d', '--no-deps', 'db')
        debut = self.horloge()
        while self.etat_conteneur('cicada_prod_db')[1] != 'healthy':
            if self.horloge() - debut > 180:
                raise ErreurMaintenance("La base de données (conteneur cicada_prod_db) ne démarre pas")
            self.dormir(3)

    def sauvegarder(self, raison, version_outil=None, fichiers=True):
        """Sauvegarde vérifiée dans un nouveau dossier. Renvoie son chemin."""
        version_outil = version_outil or self.version_paquet()
        racine = self.dossier_sauvegardes()
        racine.mkdir(parents=True, exist_ok=True)
        os.chmod(racine, 0o700)
        nom = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + re.sub(r'[^A-Za-z0-9._-]+', '-', raison)
        dossier, n = racine / nom, 1
        while dossier.exists():  # deux sauvegardes dans la même seconde
            n += 1
            dossier = racine / f'{nom}-{n}'
        nom = dossier.name
        dossier.mkdir(mode=0o700)
        self.dire(f"Sauvegarde {nom} (dans {racine})…")
        try:
            self.demarrer_base()
            resultat = self.outil_base('sauvegarder', dossier, fichiers, version_outil)
            if self.c.env.exists():
                shutil.copy2(self.c.env, dossier / 'env')
                os.chmod(dossier / 'env', 0o600)
            manifeste = {
                'date': horodatage(), 'raison': raison, 'version': self.version_en_service(),
                'version_outil': version_outil, 'base': resultat.get('base'),
                'fichiers': resultat.get('fichiers'), 'configuration': (dossier / 'env').exists(), 'ok': True,
            }
            (dossier / 'sauvegarde.json').write_text(json.dumps(manifeste, indent=1, ensure_ascii=False))
        except Exception:
            shutil.rmtree(dossier, ignore_errors=True)
            raise
        base = manifeste['base'] or {}
        self.dire(f"  ✓ sauvegarde vérifiée : base {base.get('taille', 0) // (1024 * 1024)} Mio "
                  f"({base.get('lignes')} lignes)" + (f", {manifeste['fichiers']['nombre']} fichiers déposés"
                                                       if manifeste['fichiers'] else ''))
        self.elaguer()
        return dossier

    def sauvegardes(self):
        """Sauvegardes complètes, la plus récente d'abord."""
        racine = self.dossier_sauvegardes()
        if not racine.is_dir():
            return []
        liste = []
        for d in sorted(racine.iterdir(), reverse=True):
            try:
                m = json.loads((d / 'sauvegarde.json').read_text())
            except (FileNotFoundError, NotADirectoryError, ValueError):
                continue
            if m.get('ok'):
                m['nom'] = d.name
                m['chemin'] = str(d)
                liste.append(m)
        return liste

    def trouver_sauvegarde(self, nom):
        chemin = Path(nom)
        if not chemin.is_absolute():
            chemin = self.dossier_sauvegardes() / nom
        if not (chemin / 'sauvegarde.json').exists():
            raise ErreurMaintenance(f"Sauvegarde introuvable ou incomplète : {chemin} (liste : sudo cicada-backup --liste)")
        return chemin

    def elaguer(self):
        """Garde les N plus récentes (CICADA_SAUVEGARDES_A_GARDER, défaut 5)
        et toujours celle de la dernière mise à jour."""
        garder = max(1, self.reglage('CICADA_SAUVEGARDES_A_GARDER', 5))
        t = self.tentative() or {}
        protegee = Path(t['sauvegarde']).name if t.get('sauvegarde') else None
        for m in self.sauvegardes()[garder:]:
            if m['nom'] != protegee:
                shutil.rmtree(m['chemin'], ignore_errors=True)
                self.dire(f"  sauvegarde ancienne supprimée : {m['nom']}")
        self.publier_sauvegardes()

    def publier_sauvegardes(self):
        """Résumé lu par l'application (aucun secret, aucun chemin de fichier
        de données) : dernière sauvegarde et nombre conservé."""
        liste = self.sauvegardes()
        derniere = liste[0] if liste else None
        resume = {
            'nombre': len(liste),
            'dossier': str(self.dossier_sauvegardes()),
            'derniere': {
                'nom': derniere['nom'], 'date': derniere['date'], 'raison': derniere.get('raison'),
                'version': derniere.get('version'),
                'taille': (derniere.get('base') or {}).get('taille', 0) + ((derniere.get('fichiers') or {}).get('taille', 0)),
            } if derniere else None,
        }
        try:
            self.c.echanges.mkdir(parents=True, exist_ok=True)
            chemin = self.c.echanges / 'backups.json'
            chemin.write_text(json.dumps(resume, ensure_ascii=False))
            os.chmod(chemin, 0o644)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Application : arrêt, démarrage, vérification
    # ------------------------------------------------------------------

    def arreter_application(self):
        self.compose('stop', *APPLICATION, timeout=300)

    def conserver_journal(self, t, conteneur):
        """Journal du conteneur en échec, gardé à côté de updater.log."""
        r = self.run(['docker', 'logs', '--tail', '400', conteneur])
        nom = f"maj-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{conteneur}.log"
        try:
            (self.c.journaux / nom).write_text((r.stdout or '') + (r.stderr or ''))
        except OSError:
            return None
        chemin = str(self.c.journaux / nom)
        if t is not None:
            self.noter(t, journal=chemin)
        return chemin

    @staticmethod
    def cause_lisible(journal):
        """Dernière erreur utile d'un journal de démarrage (migration…)."""
        lignes = [l.strip() for l in (journal or '').splitlines() if l.strip()]
        for motif in (r'(django\.db\.\S+Error|psycopg\S*|\w+Error|\w+Exception): .+', r'ERREUR|ERROR|FATAL'):
            for ligne in reversed(lignes):
                if re.search(motif, ligne):
                    return ligne[:300]
        return lignes[-1][:300] if lignes else ''

    def attendus(self):
        noms = dict(DEPENDANTS)
        if self.traefik():
            noms[TRAEFIK[0]] = TRAEFIK[1]
        return noms

    def services_stables(self):
        """Services dépendants qui tournent sans redémarrer, relevés avant
        l'arrêt : une mise à jour ne doit pas casser ce qui marchait, mais un
        service déjà en échec avant elle (constaté : worker Celery qui boucle)
        ne doit pas la faire défaire."""
        attendus = self.attendus()
        avant = {n: self.etat_conteneur(c) for n, c in attendus.items()}
        self.dormir(15)
        stables = []
        for n, c in attendus.items():
            statut, _, red = self.etat_conteneur(c)
            if statut == 'running' and avant[n][0] == 'running' and red == avant[n][2]:
                stables.append(n)
        return stables

    def demarrer(self, version, fichiers_de=None, t=None, exiges=None):
        """Démarre la version et vérifie web puis les services dépendants
        (`exiges` : ceux qui doivent tourner ; défaut : tous). Renvoie None si
        tout tourne, sinon la cause de l'échec."""
        delai = self.reglage('CICADA_MAJ_DELAI_DEMARRAGE', 1800)
        fichiers_de = fichiers_de or version
        if self.base_docker():
            self.compose('up', '-d', '--no-deps', 'db', 'redis', version=version, fichiers_de=fichiers_de)
        else:
            self.compose('up', '-d', '--no-deps', 'redis', version=version, fichiers_de=fichiers_de)
        r = self.compose('up', '-d', '--no-deps', 'web', version=version, fichiers_de=fichiers_de)
        if r.returncode != 0:
            return f"Démarrage du conteneur web impossible : {self.resume(r, 300)}"
        # Docker garde le compteur d'un conteneur relancé sans être recréé (retour
        # à la version de départ) : seuls comptent les redémarrages d'après.
        avant = self.etat_conteneur(WEB)[2]
        debut = self.horloge()
        self.dire(f"  démarrage de la version {version} (migrations, référentiels)…")
        while True:
            statut, sante, redemarrages = self.etat_conteneur(WEB)
            if sante == 'healthy':
                break
            if statut in ('exited', 'dead', 'restarting', 'absent') or redemarrages > avant:
                chemin = self.conserver_journal(t, WEB)
                journal = Path(chemin).read_text() if chemin else ''
                cause = self.cause_lisible(journal)
                return "L'application ne démarre pas" + (f" : {cause}" if cause else '')
            if self.horloge() - debut > delai:
                self.conserver_journal(t, WEB)
                return f"L'application n'est pas prête après {delai // 60} min"
            self.dormir(10)

        r = self.compose('up', '-d', version=version, fichiers_de=fichiers_de)
        if r.returncode != 0:
            return f"Démarrage des services impossible : {self.resume(r, 300)}"
        attendus = self.attendus()
        exiges = set(attendus) if exiges is None else set(exiges) & set(attendus)
        # Un service qui se lance pendant que ses dépendances chauffent peut
        # redémarrer une ou deux fois (constaté : celery-beat) : ce qui compte,
        # c'est qu'il finisse par tourner SANS redémarrer pendant TENUE secondes.
        tenue, delai_services = 30, 240
        debut = self.horloge()
        dernier = {n: None for n in attendus}       # (statut, redémarrages) au dernier relevé
        depuis = {n: debut for n in attendus}       # instant du dernier changement
        while True:
            maintenant = self.horloge()
            etats = {n: self.etat_conteneur(c) for n, c in attendus.items()}
            for n, (statut, sante, red) in etats.items():
                if statut != 'running' or sante == 'unhealthy' or dernier[n] != (statut, red):
                    depuis[n] = maintenant
                dernier[n] = (statut, red)
            tiennent = {n for n, (statut, sante, _) in etats.items()
                        if statut == 'running' and sante != 'unhealthy' and maintenant - depuis[n] >= tenue}
            if exiges <= tiennent:
                autres = [n for n in attendus if n not in exiges and n not in tiennent]
                if autres and t is not None:
                    self.noter(t, avertissement=(
                        f"Service(s) {', '.join(autres)} déjà en échec avant la mise à jour, toujours en échec : "
                        f"à examiner (sudo docker logs {attendus[autres[0]]})"))
                return None
            if maintenant - debut > delai_services:
                ko = sorted(exiges - tiennent)
                self.conserver_journal(t, attendus[ko[0]])
                statut, _, red = etats[ko[0]]
                return (f"Service {ko[0]} instable après le démarrage ({statut}, {red} redémarrages)"
                        if statut != 'absent' else f"Service {ko[0]} non démarré")
            self.dormir(5)

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def images(self, version):
        r = self.compose('config', '--images', version=version)
        if r.returncode != 0:
            raise ErreurMaintenance(f"Configuration Docker illisible : {self.resume(r, 300)}")
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]

    def image_presente(self, image):
        return self.run(['docker', 'image', 'inspect', image]).returncode == 0

    def tirer_images(self, version):
        """Images de la version, avant tout arrêt. Celles de CICADA ne changent
        jamais pour un numéro donné : déjà présentes, elles ne sont pas
        retéléchargées."""
        for image in self.images(version):
            if image.startswith(IMAGES_CICADA) and self.image_presente(image):
                continue
            self.dire(f"  téléchargement de {image}…")
            r = self.run(['docker', 'pull', '-q', image], timeout=1800)
            if r.returncode != 0:
                raise ErreurMaintenance(f"Téléchargement de {image} impossible : {self.resume(r, 300)}")

    def nettoyer_images(self, garder):
        """Supprime les images CICADA des versions antérieures, sauf celles à
        garder (version en service et précédente, pour un retour rapide)."""
        for depot in IMAGES_CICADA:
            r = self.run(['docker', 'image', 'ls', '--format', '{{.Repository}}:{{.Tag}}', depot])
            for image in (r.stdout or '').split():
                tag = image.rsplit(':', 1)[-1]
                if re.fullmatch(r'\d+\.\d+\.\d+', tag) and tag not in garder:
                    if self.run(['docker', 'image', 'rm', image]).returncode == 0:
                        self.dire(f"  image supprimée : {image}")
        self.run(['docker', 'image', 'prune', '-f'])

    def controler_espace(self):
        minimum = self.reglage('CICADA_MAJ_ESPACE_MIN_GO', 5)
        r = self.run(['docker', 'info', '-f', '{{.DockerRootDir}}'])
        racine = (r.stdout or '').strip() if r.returncode == 0 else ''
        racine = racine or '/var/lib/docker'
        libre = self.espace_libre(racine) / 1024 ** 3
        if libre < minimum:
            raise ErreurMaintenance(
                f"Espace disque insuffisant pour les images ({libre:.1f} Go libres dans {racine}, {minimum} Go demandés). "
                "Faire de la place (anciennes images : sudo docker image prune -a) puis relancer : sudo cicada-update retry")
        precedente = self.sauvegardes()[:1]
        besoin = 1024 ** 3
        if precedente:
            p = precedente[0]
            besoin = max(besoin, 2 * ((p.get('base') or {}).get('taille', 0) + (p.get('fichiers') or {}).get('taille', 0)))
        cible = self.dossier_sauvegardes()
        existant = cible if cible.exists() else cible.parent
        libre_sv = self.espace_libre(str(existant))
        if libre_sv < besoin:
            raise ErreurMaintenance(
                f"Espace disque insuffisant pour la sauvegarde ({libre_sv / 1024 ** 3:.1f} Go libres dans {existant}, "
                f"{besoin / 1024 ** 3:.1f} Go demandés)")

    # ------------------------------------------------------------------
    # Mise à jour
    # ------------------------------------------------------------------

    def deployer(self, cible=None, origine='paquet', forcer=False):
        """Fait tourner la version du paquet installé (ou `cible`). Renvoie la
        tentative (dict) ; son statut donne le code de sortie."""
        if not self.installee():
            self.dire("Instance pas encore installée (pas de /var/lib/cicada/.env) : rien à redéployer")
            return {'statut': A_JOUR, 'cible': cible or self.version_paquet()}
        verrou = self.verrou()
        try:
            self._reprendre(origine='reprise')
            cible = cible or self.version_paquet()
            depart = self.version_en_service()
            if not cible:
                raise ErreurMaintenance("Version cible inconnue (/usr/share/cicada/VERSION absent)")
            if depart == cible:
                self.dire(f"CICADA {cible} déjà en service")
                return {'statut': A_JOUR, 'cible': cible, 'depart': depart}
            precedente = self.tentative()
            if (origine == 'paquet' and not forcer and precedente and precedente.get('cible') == cible
                    and precedente.get('depart') == depart and precedente.get('statut') in (ANNULEE, RETOUR_FAIT, SANS_RETOUR)):
                # Paquet reconfiguré (dpkg --configure -a…) après un échec déjà
                # constaté : pas de nouvelle coupure sans que quelqu'un l'ait décidé.
                self.dire(f"La mise à jour vers {cible} a déjà échoué ({precedente.get('statut')}) : "
                          f"{precedente.get('cause')}\nPour réessayer : sudo cicada-update retry")
                return precedente
            return self._mettre_a_jour(depart, cible, origine)
        finally:
            verrou.close()

    def _mettre_a_jour(self, depart, cible, origine):
        t = {'id': uuid.uuid4().hex[:12], 'origine': origine, 'depart': depart, 'cible': cible,
             'debut': horodatage(), 'statut': EN_COURS, 'etape': 'controles'}
        self.noter(t)
        self.dire(f"=== Mise à jour CICADA {depart or '?'} → {cible} ===")
        try:
            self.controler_espace()
            self.noter(t, etape='images')
            self.tirer_images(cible)
        except ErreurMaintenance as e:
            return self._terminer(t, ANNULEE, f"{e} — rien n'a changé, l'application n'a pas été arrêtée")

        self.noter(t, etape='arret', services=self.services_stables())
        self.dire("  arrêt de l'application (coupure jusqu'à la fin de la mise à jour)…")
        self.arreter_application()
        self.noter(t, etape='sauvegarde')
        try:
            dossier = self.sauvegarder(f'avant-maj-{depart}-vers-{cible}', version_outil=cible)
        except ErreurMaintenance as e:
            cause = self.demarrer(depart, t=t, exiges=t.get('services'))
            if cause:
                return self._terminer(t, SANS_RETOUR, f"Sauvegarde impossible ({e}) et application non relancée : {cause}")
            return self._terminer(t, ANNULEE, f"Sauvegarde impossible : {e} — mise à jour annulée, "
                                              f"application relancée en {depart}")
        self.noter(t, sauvegarde=str(dossier), etape='bascule')
        self.ecrire_version(cible)
        self.noter(t, etape='demarrage')
        cause = self.demarrer(cible, t=t, exiges=t.get('services'))
        if cause is None:
            self.noter(t, etape='nettoyage')
            self.nettoyer_images(garder={cible, depart, self.version_paquet()})
            return self._terminer(t, REUSSIE, None)
        self.dire(f"  ✗ {cause}")
        return self.retour_arriere(t, cause)

    def retour_arriere(self, t, cause):
        """Version de départ et base d'avant la mise à jour."""
        self.noter(t, etape='retour_arriere', cause=cause)
        depart = t['depart']
        self.dire(f"  retour à la version {depart} avec la base sauvegardée avant la mise à jour…")
        self.arreter_application()
        try:
            if not t.get('sauvegarde'):
                raise ErreurMaintenance("aucune sauvegarde d'avant la mise à jour")
            self.demarrer_base()
            self.outil_base('restaurer', t['sauvegarde'], False, self._version_outil(t))
        except ErreurMaintenance as e:
            return self._terminer(t, SANS_RETOUR, f"{cause} ; restauration de la base impossible : {e}. "
                                  f"Application arrêtée, sauvegarde conservée ({t.get('sauvegarde')}). "
                                  f"Reprise : {COMMANDE_REPRISE}")
        self.ecrire_version(depart)
        cause_retour = self.demarrer(depart, t=t, exiges=t.get('services'))
        if cause_retour:
            self.arreter_application()
            return self._terminer(t, SANS_RETOUR, f"{cause} ; la version {depart} ne redémarre pas non plus : "
                                  f"{cause_retour}. Application arrêtée, base restaurée. Reprise : {COMMANDE_REPRISE}")
        return self._terminer(t, RETOUR_FAIT, f"{cause} — retour à la version {depart} effectué, "
                              "données d'avant la mise à jour")

    def _version_outil(self, t):
        """Image qui porte cicada-db : la cible (téléchargée pour la mise à
        jour), à défaut celle du paquet installé."""
        for v in (t.get('cible'), self.version_paquet()):
            if v and self.image_presente(f'{IMAGES_CICADA[0]}:{v}'):
                return v
        return t.get('cible') or self.version_paquet()

    def _terminer(self, t, statut, cause):
        self.noter(t, statut=statut, cause=cause, fin=horodatage(), etape='termine')
        self.ecrire_resultat(t)
        if statut == REUSSIE:
            self.dire(f"=== Mise à jour vers {t['cible']} terminée ===")
        elif statut == RETOUR_FAIT:
            self.dire(f"=== ÉCHEC de la mise à jour vers {t['cible']} : {cause} ===")
        else:
            self.dire(f"=== {'Mise à jour annulée' if statut == ANNULEE else 'ÉCHEC'} : {cause} ===")
        if t.get('journal'):
            self.dire(f"    journal de l'application : {t['journal']}")
        if t.get('avertissement'):
            self.dire(f"    ! {t['avertissement']}")
        return t

    def _reprendre(self, origine='reprise'):
        """Tentative interrompue (serveur redémarré, processus tué) : avant la
        bascule, l'application est relancée telle quelle ; après, retour à la
        version de départ depuis la sauvegarde d'origine."""
        t = self.tentative()
        if not t or t.get('statut') != EN_COURS:
            return None
        etape = t.get('etape')
        self.dire(f"Mise à jour {t.get('depart')} → {t.get('cible')} interrompue à l'étape « {etape} » : reprise")
        if etape in ('controles', 'images', 'arret', 'sauvegarde'):
            if self.version_en_service() != t['depart']:
                self.ecrire_version(t['depart'])
            cause = self.demarrer(t['depart'], t=t, exiges=t.get('services'))
            if cause:
                return self._terminer(t, SANS_RETOUR, f"Mise à jour interrompue, application non relancée : {cause}")
            return self._terminer(t, ANNULEE, "Mise à jour interrompue avant la bascule : application relancée "
                                              f"en {t['depart']}")
        if etape == 'nettoyage':
            return self._terminer(t, REUSSIE, None)
        return self.retour_arriere(t, "Mise à jour interrompue")

    def reprendre(self):
        verrou = self.verrou()
        try:
            return self._reprendre()
        finally:
            verrou.close()

    def revenir(self, confirme=False):
        """Retour manuel à la version d'avant la dernière mise à jour."""
        verrou = self.verrou()
        try:
            t = self.tentative()
            if not t:
                raise ErreurMaintenance("Aucune mise à jour enregistrée : rien à défaire")
            if t.get('statut') == EN_COURS:
                return self._reprendre()
            if t.get('statut') in (ANNULEE, RETOUR_FAIT):
                raise ErreurMaintenance(f"La dernière mise à jour ({t['depart']} → {t['cible']}) n'est pas en place "
                                        f"({t['statut']}) : rien à défaire")
            if t.get('statut') == REUSSIE:
                if self.version_en_service() != t['cible']:
                    raise ErreurMaintenance(f"La version en service ({self.version_en_service()}) n'est plus celle de "
                                            f"la dernière mise à jour ({t['cible']})")
                if not confirme:
                    raise ErreurMaintenance(
                        f"Retour à {t['depart']} avec la base du {t.get('debut')} : tout ce qui a été saisi depuis "
                        f"la mise à jour sera perdu. Pour confirmer : sudo cicada-update rollback --oui")
                return self.retour_arriere(t, f"Retour demandé à la version {t['depart']}")
            return self.retour_arriere(t, t.get('cause') or 'Reprise du retour arrière')
        finally:
            verrou.close()

    def installer(self, version, origine='bouton'):
        """Bouton « Mettre à jour » : paquet APT de la version, dont le postinst
        déroule la mise à jour ; si le paquet est déjà là (mise à jour annulée
        ou défaite), déroulé direct. Sans verrou ici : le postinst le prend."""
        debut = horodatage()
        self.run(['apt-get', 'update', '-qq'], timeout=600)
        installe = self.run(['dpkg-query', '-W', '-f', '${Version}', 'cicada']).stdout.strip()
        if installe == version:
            if self.version_en_service() == version:
                t = {'statut': A_JOUR, 'cible': version, 'depart': version, 'fin': horodatage()}
                self.ecrire_resultat(t)
                return t
            return self.deployer(version, origine=origine, forcer=True)
        env = dict(os.environ, CICADA_UPDATER_V2='1', DEBIAN_FRONTEND='noninteractive')
        r = self.run(['apt-get', 'install', '-y', '-qq', '-o', 'Dpkg::Options::=--force-confdef',
                      '-o', 'Dpkg::Options::=--force-confold', f'cicada={version}'], env=env, timeout=4 * 3600)
        t = self.tentative()
        if t and t.get('debut', '') >= debut and t.get('cible') == version:
            return t  # le postinst a déroulé la mise à jour et écrit son résultat
        if r.returncode != 0:
            t = {'statut': ANNULEE, 'cible': version, 'depart': self.version_en_service(), 'fin': horodatage(),
                 'cause': f"Paquet cicada {version} non installé : {self.resume(r, 400)} — rien n'a changé"}
            self.dire(t['cause'])
            self.ecrire_resultat(t)
            return t
        return self.deployer(version, origine=origine)

    # ------------------------------------------------------------------
    # Restauration manuelle
    # ------------------------------------------------------------------

    def restaurer(self, nom, fichiers=False, confirme=False):
        verrou = self.verrou()
        try:
            dossier = self.trouver_sauvegarde(nom)
            m = json.loads((dossier / 'sauvegarde.json').read_text())
            en_service = self.version_en_service()
            if cle_version(m.get('version')) > cle_version(en_service):
                raise ErreurMaintenance(
                    f"Sauvegarde faite en {m.get('version')}, plus récente que la version en service ({en_service}) : "
                    "l'application ne saurait pas lire cette base. Mettre d'abord l'instance en "
                    f"{m.get('version')} (sudo cicada-update install {m.get('version')})")
            if fichiers and not m.get('fichiers'):
                raise ErreurMaintenance("Cette sauvegarde ne contient pas les fichiers déposés")
            if not confirme:
                raise ErreurMaintenance(
                    f"La base sera remplacée par celle du {m.get('date')} ({m.get('raison')}) : tout ce qui a été "
                    f"saisi depuis sera perdu. Pour confirmer : sudo cicada-restore {dossier.name}"
                    + (' --fichiers' if fichiers else '') + ' --oui')
            self.dire(f"=== Restauration de la sauvegarde {dossier.name} ===")
            services = self.services_stables()
            self.arreter_application()
            try:
                self.demarrer_base()
                self.outil_base('restaurer', dossier, fichiers, self.version_paquet())
            except ErreurMaintenance as e:
                cause = self.demarrer(en_service, exiges=services)
                raise ErreurMaintenance(f"Restauration annulée, base inchangée : {e}"
                                        + (f" ; application non relancée : {cause}" if cause else
                                           " ; application relancée"))
            cause = self.demarrer(en_service, exiges=services)
            if cause:
                raise ErreurMaintenance(f"Base restaurée, mais l'application ne redémarre pas : {cause}")
            self.dire("=== Restauration terminée, application relancée ===")
            return dossier
        finally:
            verrou.close()

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------

    def etat(self):
        conteneurs = {}
        for nom in ['cicada_prod_db', 'cicada_prod_redis', WEB] + list(DEPENDANTS.values()):
            statut, sante, redemarrages = self.etat_conteneur(nom)
            if nom == 'cicada_prod_db' and not self.base_docker():
                continue
            conteneurs[nom] = statut + (f' ({sante})' if sante else '') + (f', {redemarrages} redémarrages' if redemarrages else '')
        return {
            'version_paquet': self.version_paquet(),
            'version_en_service': self.version_en_service(),
            'conteneurs': conteneurs,
            'derniere_tentative': self.tentative(),
            'sauvegardes': self.sauvegardes(),
            'dossier_sauvegardes': str(self.dossier_sauvegardes()),
        }


# ----------------------------------------------------------------------
# Commandes
# ----------------------------------------------------------------------

LIBELLES = {
    REUSSIE: 'réussie', A_JOUR: 'déjà à jour', ANNULEE: 'annulée (rien changé)',
    RETOUR_FAIT: 'échec — retour à la version précédente effectué',
    SANS_RETOUR: 'ÉCHEC — application arrêtée, retour arrière à reprendre', EN_COURS: 'en cours ou interrompue',
}


def afficher_etat(e, sortie=sys.stdout):
    p = lambda *a: print(*a, file=sortie)  # noqa: E731
    p(f"Version du paquet installé : {e['version_paquet'] or '?'}")
    p(f"Version en service         : {e['version_en_service'] or '?'}")
    if e['version_paquet'] and e['version_en_service'] and e['version_paquet'] != e['version_en_service']:
        p("  → le paquet est plus récent que la version en service (mise à jour annulée ou défaite) : "
          "sudo cicada-update retry")
    p("Conteneurs :")
    for nom, etat in e['conteneurs'].items():
        p(f"  {nom:28} {etat}")
    t = e['derniere_tentative']
    p("Dernière mise à jour :")
    if t:
        p(f"  {t.get('depart')} → {t.get('cible')} ({t.get('origine')}), {t.get('debut')} : "
          f"{LIBELLES.get(t.get('statut'), t.get('statut'))}")
        if t.get('cause'):
            p(f"  cause : {t['cause']}")
        if t.get('sauvegarde'):
            p(f"  sauvegarde d'avant : {t['sauvegarde']}")
        if t.get('journal'):
            p(f"  journal : {t['journal']}")
        if t.get('statut') == SANS_RETOUR:
            p(f"  → reprendre : {COMMANDE_REPRISE}")
    else:
        p("  aucune")
    afficher_sauvegardes(e['sauvegardes'], e['dossier_sauvegardes'], sortie)


def afficher_sauvegardes(liste, dossier, sortie=sys.stdout):
    print(f"Sauvegardes ({dossier}) :", file=sortie)
    if not liste:
        print("  aucune", file=sortie)
    for m in liste:
        taille = ((m.get('base') or {}).get('taille', 0) + (m.get('fichiers') or {}).get('taille', 0)) / 1024 ** 2
        print(f"  {m['nom']:52} CICADA {m.get('version') or '?':8} {taille:8.1f} Mio"
              + ('' if m.get('fichiers') else '  (base seule)'), file=sortie)


def main_update(argv=None, instance=None):
    import argparse
    parser = argparse.ArgumentParser(
        prog='cicada-update',
        description="Mise à jour de CICADA, avec sauvegarde préalable et retour arrière automatique.")
    sous = parser.add_subparsers(dest='action')
    sous.add_parser('status', help="état de l'instance, dernière mise à jour, sauvegardes")
    p = sous.add_parser('install', help='installer une version (par défaut la plus récente du dépôt)')
    p.add_argument('version', nargs='?')
    sous.add_parser('retry', help='relancer la mise à jour vers la version du paquet installé')
    p = sous.add_parser('rollback', help="revenir à la version d'avant la dernière mise à jour")
    p.add_argument('--oui', action='store_true', help='confirmer (les saisies faites depuis seront perdues)')
    sous.add_parser('resume', help='reprendre une mise à jour interrompue')
    p = sous.add_parser('deploy', help=argparse.SUPPRESS)
    p.add_argument('--origine', default='paquet')
    args = parser.parse_args(argv)
    i = instance or Instance()
    if os.geteuid() != 0 and instance is None and args.action not in (None, 'status'):
        print("À lancer en root : sudo cicada-update …", file=sys.stderr)
        return 1
    try:
        if args.action in (None, 'status'):
            afficher_etat(i.etat())
            return 0
        if args.action == 'install':
            version = args.version or candidat_apt(i)
            if not version:
                raise ErreurMaintenance("Aucune version de cicada proposée par le dépôt APT (apt-cache policy cicada)")
            t = i.installer(version, origine='commande')
        elif args.action == 'retry':
            t = i.deployer(origine='commande', forcer=True)
        elif args.action == 'rollback':
            t = i.revenir(confirme=args.oui)
        elif args.action == 'resume':
            t = i.reprendre() or {'statut': A_JOUR}
            if t.get('statut') == A_JOUR:
                print("Aucune mise à jour interrompue", file=sys.stderr)
        else:
            t = i.deployer(origine=args.origine)
    except ErreurMaintenance as e:
        print(f"ÉCHEC : {e}", file=sys.stderr)
        return 1
    return CODES.get(t.get('statut'), 1)


def candidat_apt(i):
    i.run(['apt-get', 'update', '-qq'], timeout=600)
    sortie = i.run(['apt-cache', 'policy', 'cicada']).stdout
    m = re.search(r'(?:Candidat|Candidate)\s*:\s*(\S+)', sortie)
    return m.group(1) if m and m.group(1) != '(none)' else None


def main_backup(argv=None, instance=None):
    import argparse
    parser = argparse.ArgumentParser(prog='cicada-backup',
                                     description="Sauvegarde vérifiée de CICADA : base, fichiers déposés, configuration.")
    parser.add_argument('--liste', action='store_true', help='lister les sauvegardes')
    parser.add_argument('--verifier', metavar='SAUVEGARDE', help="relire une sauvegarde (empreintes, archive entière)")
    parser.add_argument('--sans-fichiers', action='store_true', help='base et configuration seulement')
    parser.add_argument('--raison', default='manuelle', help='libellé ajouté au nom du dossier')
    args = parser.parse_args(argv)
    i = instance or Instance()
    if os.geteuid() != 0 and instance is None:
        print("À lancer en root : sudo cicada-backup …", file=sys.stderr)
        return 1
    try:
        if args.liste:
            afficher_sauvegardes(i.sauvegardes(), i.dossier_sauvegardes())
            return 0
        if not i.installee():
            raise ErreurMaintenance("Instance pas encore installée : rien à sauvegarder")
        if args.verifier:
            dossier = i.trouver_sauvegarde(args.verifier)
            i.demarrer_base()
            i.outil_base('verifier', dossier, False, i.version_paquet())
            print(f"Sauvegarde {dossier.name} intacte (empreintes et archive relue en entier)")
            return 0
        verrou = i.verrou()
        try:
            dossier = i.sauvegarder(args.raison, fichiers=not args.sans_fichiers)
        finally:
            verrou.close()
        print(dossier)
        return 0
    except ErreurMaintenance as e:
        print(f"ÉCHEC : {e}", file=sys.stderr)
        return 1


def main_restore(argv=None, instance=None):
    import argparse
    parser = argparse.ArgumentParser(
        prog='cicada-restore',
        description="Restaure une sauvegarde de la base (tout ou rien) et relance l'application.")
    parser.add_argument('sauvegarde', help='nom du dossier (sudo cicada-backup --liste) ou chemin')
    parser.add_argument('--fichiers', action='store_true', help='restaurer aussi les fichiers déposés')
    parser.add_argument('--oui', action='store_true', help='confirmer (les saisies faites depuis seront perdues)')
    args = parser.parse_args(argv)
    i = instance or Instance()
    if os.geteuid() != 0 and instance is None:
        print("À lancer en root : sudo cicada-restore …", file=sys.stderr)
        return 1
    try:
        i.restaurer(args.sauvegarde, fichiers=args.fichiers, confirme=args.oui)
        return 0
    except ErreurMaintenance as e:
        print(f"ÉCHEC : {e}", file=sys.stderr)
        return 1
