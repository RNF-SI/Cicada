"""Mise à jour, sauvegarde et restauration d'une instance (#796).

Le déroulé de `cicada_maintenance` est joué contre un serveur simulé : Docker
(conteneurs, images, registre), la base (son « schéma » suit la version qui l'a
migrée en dernier) et APT. Un cas par ligne du tableau de l'issue :

| Cas                                            | Attendu                                   |
|------------------------------------------------|-------------------------------------------|
| images introuvables, disque plein              | annulée, rien n'a changé, rien d'arrêté    |
| sauvegarde impossible                          | annulée, application relancée telle quelle |
| migration en échec / service qui ne tient pas  | retour automatique, base d'avant           |
| serveur redémarré pendant la mise à jour       | reprise depuis la sauvegarde d'origine     |
| le retour arrière échoue aussi                 | arrêtée, sauvegarde gardée, commande donnée|

Lancement : packaging/check-installer.sh
"""
import copy
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

RACINE_PAQUET = pathlib.Path(__file__).resolve().parents[1] / 'debian'
sys.path.insert(0, str(RACINE_PAQUET / 'usr/share/cicada/maintenance'))

import cicada_maintenance as cm  # noqa: E402

BACKEND = 'ghcr.io/rnf-si/cicada-backend'
FRONTEND = 'ghcr.io/rnf-si/cicada-frontend'
SERVICES = {
    'web': 'cicada_prod_web', 'frontend': 'cicada_prod_frontend', 'celery-worker': 'cicada_prod_celery_worker',
    'celery-beat': 'cicada_prod_celery_beat', 'db': 'cicada_prod_db', 'redis': 'cicada_prod_redis',
}


def images_de(v):
    return [f'{BACKEND}:{v}', f'{FRONTEND}:{v}', 'redis:7-alpine', 'postgis/postgis:17-3.5-alpine']


class Serveur:
    """Serveur simulé : répond aux commandes que lance cicada_maintenance."""

    def __init__(self, racine, depart='1.0.0'):
        self.racine = racine
        self.temps = 0.0
        self.appels = []
        self.registre = set(images_de('1.0.0') + images_de('1.1.0'))
        self.images = set(images_de(depart)) | {f'{BACKEND}:0.9.0', f'{FRONTEND}:0.9.0'}
        self.conteneurs = {}
        # La base : version qui l'a migrée en dernier, et les données saisies
        self.base = {'schema': depart, 'donnees': ['plan A', 'plan B']}
        self.archives = {}
        self.web_casse = set()          # versions dont les migrations échouent
        self.dependants_casses = set()  # versions dont le frontend s'arrête
        self.toujours_casses = set()    # services qui bouclent dans toutes les versions
        self.demarrages_instables = {}  # service → redémarrages au lancement, puis il tient
        self.outil_en_echec = {}        # action cicada-db → message
        self.archives_illisibles = set()  # sauvegardes dont la restauration échoue
        self.sans_outil = set()         # versions dont l'image n'a pas cicada-db (antérieures à #796)
        self.paquet = depart
        self.depot_apt = {'1.0.0', '1.1.0'}
        self.postinst = None            # appelé par « apt-get install » (déroulé du paquet)
        for service in ('db', 'redis', 'web', 'frontend', 'celery-worker', 'celery-beat'):
            self.demarrer(service, depart)
        # À l'installation, les tâches de fond démarrent avant la base et
        # redémarrent quelques fois : constaté sur le banc VM (#796).
        self.conteneurs['cicada_prod_celery_worker']['redemarrages'] = 2
        self.conteneurs['cicada_prod_web']['redemarrages'] = 1

    # -- commandes ---------------------------------------------------------
    def __call__(self, cmd, capture_output=True, text=True, env=None, timeout=None):
        self.appels.append(cmd)
        ok = lambda out='': subprocess.CompletedProcess(cmd, 0, out, '')  # noqa: E731
        ko = lambda err, code=1: subprocess.CompletedProcess(cmd, code, '', err)  # noqa: E731
        if cmd[:2] == ['docker', 'compose']:
            return self.compose(cmd, env or {})
        if cmd[:2] == ['docker', 'inspect']:
            if 'com.docker.compose.project' in cmd[3]:
                return ok('cicada\n')
            c = self.conteneurs.get(cmd[-1])
            if not c:
                return ko('No such object')
            if c['statut'] == 'restarting':
                c['redemarrages'] += 1
                if 'a_tenir' in c:
                    c['a_tenir'] -= 1
                    if c['a_tenir'] <= 0:
                        c['statut'] = 'running'
                        del c['a_tenir']
            return ok(f"{c['statut']}|{c['sante']}|{c['redemarrages']}\n")
        if cmd[:3] == ['docker', 'image', 'inspect']:
            return ok() if cmd[3] in self.images else ko('No such image')
        if cmd[:2] == ['docker', 'pull']:
            if cmd[-1] in self.registre:
                self.images.add(cmd[-1])
                return ok()
            return ko(f'manifest for {cmd[-1]} not found')
        if cmd[:3] == ['docker', 'image', 'ls']:
            return ok('\n'.join(sorted(i for i in self.images if i.startswith(cmd[-1] + ':'))))
        if cmd[:3] == ['docker', 'image', 'rm']:
            self.images.discard(cmd[3])
            return ok()
        if cmd[:2] == ['docker', 'info']:
            return ok('/var/lib/docker\n')
        if cmd[:2] == ['docker', 'logs']:
            return ok('=== Application des migrations ===\n'
                      'django.db.utils.ProgrammingError: relation "t_nouvelle" already exists\n')
        if cmd[:2] in (['docker', 'rm'],) or cmd[:3] == ['docker', 'image', 'prune']:
            return ok()
        if cmd[:2] == ['apt-get', 'update']:
            return ok()
        if cmd[:2] == ['apt-get', 'install']:
            version = cmd[-1].split('=', 1)[1]
            if version not in self.depot_apt:
                return ko(f"E: Version '{version}' for 'cicada' was not found", 100)
            self.paquet = version
            (self.racine / 'usr/share/cicada/VERSION').write_text(version + '\n')
            if self.postinst:
                self.postinst()
            return ok()
        if cmd[0] == 'dpkg-query':
            return ok(self.paquet)
        raise AssertionError(f'commande inattendue : {cmd}')

    def compose(self, cmd, env):
        i = cmd.index('--env-file')
        args = cmd[i + 2:]
        fichiers = [cmd[j + 1] for j, a in enumerate(cmd[:i]) if a == '-f']
        version = env.get('CICADA_VERSION') or self.version_env()
        ok = lambda out='': subprocess.CompletedProcess(cmd, 0, out, '')  # noqa: E731
        if args[:2] == ['config', '--images']:
            return ok('\n'.join(images_de(version)) + '\n')
        if args[0] == 'stop':
            for service in args[1:]:
                if SERVICES[service] in self.conteneurs:
                    self.conteneurs[SERVICES[service]].update(statut='exited', sante='')
            return ok()
        if args[:2] == ['up', '-d']:
            services = [a for a in args[2:] if not a.startswith('-')] or \
                ['db', 'redis', 'web', 'frontend', 'celery-worker', 'celery-beat']
            self.derniers_fichiers = fichiers
            for service in services:
                c = self.conteneurs.get(SERVICES[service])
                if c and c['version'] == version and c['statut'] == 'running':
                    continue
                if not self.demarrer(service, version):
                    return subprocess.CompletedProcess(cmd, 1, '', f'pull access denied for {version}')
            return ok()
        if args[0] == 'run':
            dossier = pathlib.Path(args[args.index('-v') + 1].split(':')[0])
            action = args[args.index('web') + 1]
            if f'{BACKEND}:{version}' not in self.images:
                return subprocess.CompletedProcess(cmd, 1, '', 'image absente')
            if version in self.sans_outil:
                return subprocess.CompletedProcess(cmd, 127, '', 'exec: "cicada-db": executable file not found in $PATH')
            if action in self.outil_en_echec:
                return ok(json.dumps({'ok': False, 'erreur': self.outil_en_echec[action]}))
            if action == 'sauvegarder':
                self.archives[str(dossier)] = copy.deepcopy(self.base)
                (dossier / 'base.json').write_text('{}')
                resultat = {'base': {'taille': 4096, 'lignes': len(self.base['donnees'])}}
                if '--fichiers' in args:
                    resultat['fichiers'] = {'taille': 100, 'nombre': 3}
                return ok('Sauvegarde…\n' + json.dumps({'ok': True, **resultat}))
            if action == 'restaurer' and str(dossier) in self.archives_illisibles:
                return ok(json.dumps({'ok': False, 'erreur': "Restauration annulée, la base n'a pas été modifiée"}))
            if action == 'restaurer':
                self.base = copy.deepcopy(self.archives[str(dossier)])
                return ok(json.dumps({'ok': True, 'base': {}}))
            return ok(json.dumps({'ok': True}))
        raise AssertionError(f'compose inattendu : {args}')

    def demarrer(self, service, version):
        nom = SERVICES[service]
        if service in ('web', 'frontend', 'celery-worker', 'celery-beat'):
            image = f'{FRONTEND if service == "frontend" else BACKEND}:{version}'
            if image not in self.images:
                return False
        # Docker garde le compteur de redémarrages d'un conteneur relancé sans
        # être recréé (même version) : il ne dit rien du démarrage en cours.
        ancien = self.conteneurs.get(nom)
        historique = ancien['redemarrages'] if ancien and ancien['version'] == version else 0
        etat = {'statut': 'running', 'sante': '', 'redemarrages': historique, 'version': version}
        if service in ('web', 'db', 'redis'):
            etat['sante'] = 'healthy'
        if service == 'web':
            if version in self.web_casse:
                # Migrations à moitié passées, puis redémarrages en boucle
                self.base['schema'] = f'partielle-{version}'
                if 'écrit par la migration' not in self.base['donnees']:
                    self.base['donnees'].append('écrit par la migration')
                etat.update(statut='restarting', sante='starting', redemarrages=historique + 3)
            elif not self.base['schema'].startswith('partielle'):
                # Une version ne défait jamais les migrations d'une autre : seule
                # la restauration de la sauvegarde rend la base d'avant.
                self.base['schema'] = max(self.base['schema'], version, key=cm.cle_version)
        if service == 'frontend' and version in self.dependants_casses:
            etat.update(statut='restarting', redemarrages=historique + 2)
        if service in self.toujours_casses:
            etat.update(statut='restarting', redemarrages=historique + 2)
        if self.demarrages_instables.get(service):
            etat.update(statut='restarting', a_tenir=self.demarrages_instables[service])
        self.conteneurs[nom] = etat
        return True

    # -- état --------------------------------------------------------------
    def version_env(self):
        for ligne in (self.racine / 'var/lib/cicada/.env').read_text().splitlines():
            if ligne.startswith('CICADA_VERSION='):
                return ligne.split('=', 1)[1]
        return ''

    def dormir(self, secondes):
        self.temps += secondes

    def arrets(self):
        return [c for c in self.appels if 'stop' in c and c[:2] == ['docker', 'compose']]

    def application_en_service(self):
        web = self.conteneurs['cicada_prod_web']
        return web['statut'] == 'running' and web['sante'] == 'healthy', web['version']


@pytest.fixture
def instance(tmp_path):
    (tmp_path / 'var/lib/cicada/updates').mkdir(parents=True)
    (tmp_path / 'usr/share/cicada').mkdir(parents=True)
    for nom in ('docker-compose.yml', 'docker-compose.db.yml', 'docker-compose.frontend-ports.yml'):
        (tmp_path / 'usr/share/cicada' / nom).write_text('# paquet\n')
    (tmp_path / 'usr/share/cicada/VERSION').write_text('1.1.0\n')
    env = tmp_path / 'var/lib/cicada/.env'
    env.write_text('SECRET_KEY=secret\nCICADA_VERSION=1.0.0\nDB_TYPE=docker\n')
    env.chmod(0o600)
    # Copie faite par le preinst des fichiers compose de la version remplacée
    copie = tmp_path / 'var/lib/cicada/maintenance/compose/1.0.0'
    copie.mkdir(parents=True)
    for nom in ('docker-compose.yml', 'docker-compose.db.yml', 'docker-compose.frontend-ports.yml'):
        (copie / nom).write_text('# 1.0.0\n')
    serveur = Serveur(tmp_path)
    serveur.paquet = '1.1.0'
    i = cm.Instance(chemins=cm.Chemins(tmp_path), executer=serveur, dormir=serveur.dormir,
                    horloge=lambda: serveur.temps, espace_libre=lambda chemin: 50 * 1024 ** 3,
                    sortie=io.StringIO())
    i.serveur = serveur
    i.racine = tmp_path
    return i


def resultat(i):
    return json.loads((i.racine / 'var/lib/cicada/updates/update_result.json').read_text())


def version_env(i):
    return i.serveur.version_env()


# ---------------------------------------------------------------------------

def test_mise_a_jour_reussie(instance):
    t = instance.deployer()

    assert t['statut'] == cm.REUSSIE
    assert version_env(instance) == '1.1.0'
    assert instance.serveur.application_en_service() == (True, '1.1.0')
    assert instance.serveur.base['schema'] == '1.1.0'
    assert instance.serveur.base['donnees'] == ['plan A', 'plan B']
    sauvegarde = pathlib.Path(t['sauvegarde'])
    manifeste = json.loads((sauvegarde / 'sauvegarde.json').read_text())
    assert manifeste['ok'] and manifeste['version'] == '1.0.0' and manifeste['fichiers']['nombre'] == 3
    assert (sauvegarde / 'env').read_text().startswith('SECRET_KEY=')
    # Fichiers de déploiement de la version sauvegardée (#800)
    assert (sauvegarde / 'compose/docker-compose.yml').read_text() == '# 1.0.0\n'
    assert manifeste['compose'] is True
    assert oct((sauvegarde / 'env').stat().st_mode)[-3:] == '600'
    assert oct((instance.racine / 'var/lib/cicada/.env').stat().st_mode)[-3:] == '600'
    r = resultat(instance)
    assert r['success'] is True and r['statut'] == 'reussie' and r['version'] == '1.1.0'
    # Images : la version précédente est gardée pour un retour rapide, les plus anciennes partent
    assert f'{BACKEND}:1.0.0' in instance.serveur.images
    assert f'{BACKEND}:0.9.0' not in instance.serveur.images
    publie = json.loads((instance.racine / 'var/lib/cicada/updates/backups.json').read_text())
    assert publie['nombre'] == 1 and publie['derniere']['version'] == '1.0.0'


def test_images_introuvables_rien_ne_change(instance):
    instance.serveur.registre.discard(f'{BACKEND}:1.1.0')

    t = instance.deployer()

    assert t['statut'] == cm.ANNULEE
    assert 'rien n\'a changé' in t['cause'] and 'cicada-backend:1.1.0' in t['cause']
    assert instance.serveur.arrets() == []
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.application_en_service() == (True, '1.0.0')
    r = resultat(instance)
    assert r['success'] is False and r['statut'] == 'annulee'


def test_disque_plein_rien_ne_change(instance):
    instance.espace_libre = lambda chemin: 1 * 1024 ** 3

    t = instance.deployer()

    assert t['statut'] == cm.ANNULEE
    assert 'Espace disque insuffisant' in t['cause']
    assert not [c for c in instance.serveur.appels if c[:2] == ['docker', 'pull']]
    assert instance.serveur.arrets() == []
    assert version_env(instance) == '1.0.0'


def test_sauvegarde_impossible_application_relancee_telle_quelle(instance):
    instance.serveur.outil_en_echec['sauvegarder'] = 'pg_dump a échoué : permission refusée'

    t = instance.deployer()

    assert t['statut'] == cm.ANNULEE
    assert 'Sauvegarde impossible' in t['cause'] and 'permission refusée' in t['cause']
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.application_en_service() == (True, '1.0.0')
    assert instance.serveur.base['schema'] == '1.0.0'
    assert instance.sauvegardes() == []  # pas de sauvegarde incomplète laissée


def test_migration_en_echec_retour_automatique(instance):
    instance.serveur.web_casse.add('1.1.0')

    t = instance.deployer()

    assert t['statut'] == cm.RETOUR_FAIT
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.application_en_service() == (True, '1.0.0')
    # Base d'avant la mise à jour, pas celle à moitié migrée
    assert instance.serveur.base == {'schema': '1.0.0', 'donnees': ['plan A', 'plan B']}
    # Relancée avec SES fichiers compose (copie du preinst)
    assert all('maintenance/compose/1.0.0' in f for f in instance.serveur.derniers_fichiers)
    r = resultat(instance)
    assert r['success'] is False and r['retour_arriere'] is True and r['statut'] == 'echec_retour_fait'
    assert 'ProgrammingError' in r['error'] and 'retour à la version 1.0.0 effectué' in r['error']
    journal = pathlib.Path(r['journal'])
    assert journal.exists() and 'already exists' in journal.read_text()


def test_service_dependant_en_echec_retour_automatique(instance):
    instance.serveur.dependants_casses.add('1.1.0')

    t = instance.deployer()

    assert t['statut'] == cm.RETOUR_FAIT
    assert 'frontend' in t['cause']
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.application_en_service() == (True, '1.0.0')
    assert instance.serveur.conteneurs['cicada_prod_frontend']['version'] == '1.0.0'


def test_service_qui_bouclait_deja_ne_bloque_pas_la_mise_a_jour(instance):
    """Une mise à jour ne doit pas casser ce qui marchait ; un service déjà en
    échec avant (constaté : worker Celery) ne la fait pas défaire, il est signalé."""
    serveur = instance.serveur
    serveur.toujours_casses.add('celery-worker')
    serveur.demarrer('celery-worker', '1.0.0')

    t = instance.deployer()

    assert t['statut'] == cm.REUSSIE
    assert version_env(instance) == '1.1.0'
    assert 'celery-worker' in t['avertissement']
    assert 'celery-worker' in resultat(instance)['avertissement']


def test_service_qui_redemarre_au_lancement_puis_tient_n_est_pas_un_echec(instance):
    """Constaté sur le banc VM : celery-beat redémarre deux fois au retour en
    version de départ, puis tient. Seul compte un service qui ne tient pas."""
    serveur = instance.serveur
    serveur.web_casse.add('1.1.0')
    serveur.demarrages_instables = {'celery-beat': 2}

    t = instance.deployer()

    assert t['statut'] == cm.RETOUR_FAIT
    assert instance.serveur.application_en_service() == (True, '1.0.0')


def test_retour_arriere_impossible_puis_reprise(instance):
    instance.serveur.web_casse.add('1.1.0')
    instance.serveur.outil_en_echec['restaurer'] = 'connexion à la base impossible'

    t = instance.deployer()

    assert t['statut'] == cm.SANS_RETOUR
    assert 'sudo cicada-update rollback' in t['cause']
    sauvegarde = pathlib.Path(t['sauvegarde'])
    assert (sauvegarde / 'sauvegarde.json').exists()  # sauvegarde intacte
    assert instance.serveur.conteneurs['cicada_prod_web']['statut'] == 'exited'  # laissée arrêtée
    r = resultat(instance)
    assert r['statut'] == 'echec_sans_retour' and r['commande'] == 'sudo cicada-update rollback'

    # La cause réglée, la commande donnée termine le retour arrière
    del instance.serveur.outil_en_echec['restaurer']
    t = instance.revenir()

    assert t['statut'] == cm.RETOUR_FAIT
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.application_en_service() == (True, '1.0.0')
    assert instance.serveur.base == {'schema': '1.0.0', 'donnees': ['plan A', 'plan B']}


def tentative_interrompue(instance, etape):
    """État laissé par une mise à jour coupée (serveur redémarré) à cette étape."""
    serveur = instance.serveur
    dossier = instance.sauvegarder('avant-maj-1.0.0-vers-1.1.0', version_outil='1.0.0')
    serveur.images |= set(images_de('1.1.0'))
    t = {'id': 'x', 'origine': 'bouton', 'depart': '1.0.0', 'cible': '1.1.0', 'debut': '2026-11-06T10:00:00+01:00',
         'statut': cm.EN_COURS, 'etape': etape}
    if etape in ('bascule', 'demarrage'):
        t['sauvegarde'] = str(dossier)
        instance.ecrire_version('1.1.0')
        serveur.base['schema'] = 'partielle-1.1.0'
        serveur.base['donnees'].append('écrit par la migration')
    for c in ('cicada_prod_web', 'cicada_prod_frontend', 'cicada_prod_celery_worker', 'cicada_prod_celery_beat'):
        serveur.conteneurs[c].update(statut='exited', sante='')
    instance.noter(t)


def test_interruption_apres_la_bascule_reprise_depuis_la_sauvegarde(instance):
    tentative_interrompue(instance, 'demarrage')

    t = instance.reprendre()

    assert t['statut'] == cm.RETOUR_FAIT
    assert 'interrompue' in t['cause']
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.base == {'schema': '1.0.0', 'donnees': ['plan A', 'plan B']}
    assert instance.serveur.application_en_service() == (True, '1.0.0')


def test_interruption_avant_la_bascule_application_relancee(instance):
    tentative_interrompue(instance, 'sauvegarde')

    t = instance.reprendre()

    assert t['statut'] == cm.ANNULEE
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.application_en_service() == (True, '1.0.0')
    assert not [c for c in instance.serveur.appels if 'restaurer' in c]


def test_sans_tentative_interrompue_la_reprise_ne_fait_rien(instance):
    assert instance.reprendre() is None
    assert instance.serveur.arrets() == []


def test_paquet_reconfigure_apres_un_echec_pas_de_nouvelle_coupure(instance):
    """dpkg --configure -a après un échec : pas de nouvelle tentative sans décision."""
    instance.serveur.web_casse.add('1.1.0')
    instance.deployer()
    arrets = len(instance.serveur.arrets())

    t = instance.deployer(origine='paquet')

    assert t['statut'] == cm.RETOUR_FAIT
    assert len(instance.serveur.arrets()) == arrets

    # Une décision explicite (cicada-update retry, bouton) relance
    instance.serveur.web_casse.clear()
    t = instance.deployer(origine='commande', forcer=True)
    assert t['statut'] == cm.REUSSIE
    assert version_env(instance) == '1.1.0'


def test_deja_a_jour(instance):
    instance.ecrire_version('1.1.0')
    t = instance.deployer()
    assert t['statut'] == cm.A_JOUR
    assert instance.serveur.arrets() == []


def test_retour_manuel_apres_une_mise_a_jour_reussie_demande_confirmation(instance):
    instance.deployer()
    instance.serveur.base['donnees'].append('saisi après la mise à jour')

    with pytest.raises(cm.ErreurMaintenance, match='--oui'):
        instance.revenir()
    assert version_env(instance) == '1.1.0'

    t = instance.revenir(confirme=True)
    assert t['statut'] == cm.RETOUR_FAIT
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.base['donnees'] == ['plan A', 'plan B']
    # Retour voulu, pas un échec : la page de mise à jour n'affiche pas « a échoué »
    r = resultat(instance)
    assert r['statut'] == 'retour_demande' and r['success'] is True and r['retour_arriere'] is True


def test_rollback_demande_rend_0(instance):
    instance.deployer()
    assert cm.main_update(['rollback', '--oui'], instance=instance) == 0
    assert version_env(instance) == '1.0.0'


# --- Bouton « Mettre à jour » : paquet APT, puis déroulé par le postinst ------------

def brancher_postinst(instance):
    instance.serveur.paquet = '1.0.0'
    (instance.racine / 'usr/share/cicada/VERSION').write_text('1.0.0\n')
    instance.serveur.postinst = lambda: instance.deployer(origine='paquet')


def test_bouton_installe_le_paquet_dont_le_postinst_met_a_jour(instance):
    brancher_postinst(instance)

    t = instance.installer('1.1.0')

    assert t['statut'] == cm.REUSSIE
    assert instance.serveur.paquet == '1.1.0'
    assert version_env(instance) == '1.1.0'
    install = [c for c in instance.serveur.appels if c[:2] == ['apt-get', 'install']][0]
    assert 'cicada=1.1.0' in install and 'Dpkg::Options::=--force-confold' in install


def test_bouton_version_absente_du_depot_rien_ne_change(instance):
    brancher_postinst(instance)

    t = instance.installer('1.2.0')

    assert t['statut'] == cm.ANNULEE
    assert "rien n'a changé" in t['cause'] and 'was not found' in t['cause']
    assert instance.serveur.arrets() == []
    assert resultat(instance)['statut'] == 'annulee'


def test_bouton_paquet_deja_installe_apres_un_echec(instance):
    """Paquet 1.1.0 installé, application revenue en 1.0.0 : le bouton relance
    la mise à jour sans réinstaller le paquet (apt ne rejouerait pas le postinst)."""
    instance.serveur.web_casse.add('1.1.0')
    instance.deployer()
    instance.serveur.web_casse.clear()

    t = instance.installer('1.1.0')

    assert t['statut'] == cm.REUSSIE
    assert not [c for c in instance.serveur.appels if c[:2] == ['apt-get', 'install']]
    assert version_env(instance) == '1.1.0'


def test_bouton_redemande_la_version_en_service_garde_le_compte_rendu(instance):
    """Staging 13/11 (0.1.69 → 0.1.72) : une 2e demande du bouton, arrivée pendant
    la mise à jour, a relancé l'updater juste après ; son « déjà à jour » a
    remplacé la réussite et l'avertissement du worker sur la page."""
    brancher_postinst(instance)
    instance.serveur.paquet = '1.0.0'
    assert instance.installer('1.1.0')['statut'] == cm.REUSSIE
    avant = resultat(instance)
    assert avant['statut'] == 'reussie'

    t = instance.installer('1.1.0')

    assert t['statut'] == cm.A_JOUR
    assert resultat(instance) == avant


def test_bouton_version_en_service_sans_compte_rendu_ecrit_a_jour(instance):
    instance.ecrire_version('1.1.0')
    instance.serveur.paquet = '1.1.0'

    assert instance.installer('1.1.0')['statut'] == cm.A_JOUR
    assert resultat(instance)['statut'] == 'a_jour'


# --- Sauvegardes et restauration ---------------------------------------------------

def test_conservation_limitee_sauf_la_sauvegarde_de_la_derniere_mise_a_jour(instance):
    env = instance.racine / 'var/lib/cicada/.env'
    env.write_text(env.read_text() + 'CICADA_SAUVEGARDES_A_GARDER=2\n')
    t = instance.deployer()
    noms = []
    for n in range(3):
        noms.append(instance.sauvegarder(f'quotidienne-{n}').name)

    gardees = [m['nom'] for m in instance.sauvegardes()]
    assert gardees[:2] == [noms[2], noms[1]]
    assert pathlib.Path(t['sauvegarde']).name in gardees
    assert noms[0] not in gardees


def test_restauration_manuelle(instance):
    dossier = instance.sauvegarder('manuelle', version_outil='1.0.0')
    instance.serveur.base['donnees'].append('saisie à perdre')

    with pytest.raises(cm.ErreurMaintenance, match='--oui'):
        instance.restaurer(dossier.name)
    assert 'saisie à perdre' in instance.serveur.base['donnees']

    instance.restaurer(dossier.name, confirme=True)
    assert instance.serveur.base['donnees'] == ['plan A', 'plan B']
    assert instance.serveur.application_en_service() == (True, '1.0.0')


def test_restauration_refusee_d_une_sauvegarde_plus_recente(instance):
    instance.deployer()
    dossier = instance.sauvegarder('apres-maj')
    instance.ecrire_version('1.0.0')

    with pytest.raises(cm.ErreurMaintenance, match='plus récente.*--avec-sa-version'):
        instance.restaurer(dossier.name, confirme=True)


# --- Retour à une version plus ancienne depuis une sauvegarde (#800) ---------------

def monter(instance, version):
    """Nouveau paquet comme apt le pose : le preinst copie les fichiers compose
    de la version remplacée, puis le postinst déroule la mise à jour."""
    serveur, racine = instance.serveur, instance.racine
    copie = racine / 'var/lib/cicada/maintenance/compose' / serveur.paquet
    copie.mkdir(parents=True, exist_ok=True)
    for f in (racine / 'usr/share/cicada').glob('docker-compose*.yml'):
        (copie / f.name).write_text(f.read_text())
    for f in (racine / 'usr/share/cicada').glob('docker-compose*.yml'):
        f.write_text(f'# {version}\n')
    (racine / 'usr/share/cicada/VERSION').write_text(version + '\n')
    serveur.paquet = version
    serveur.registre |= set(images_de(version))
    serveur.depot_apt = {version}
    t = instance.deployer(origine='paquet')
    assert t['statut'] == cm.REUSSIE
    return t


@pytest.fixture
def trois_versions(instance):
    """Sauvegarde quotidienne faite en 1.0.0, puis deux mises à jour (1.1.0,
    1.2.0) et des saisies ; la copie du preinst et les images de 1.0.0 ont
    disparu depuis (le paquet n'en garde que 5, le nettoyage les a retirées)."""
    for nom in ('docker-compose.yml', 'docker-compose.db.yml', 'docker-compose.frontend-ports.yml'):
        (instance.racine / 'usr/share/cicada' / nom).write_text('# 1.1.0\n')
    sauvegarde = instance.sauvegarder('quotidienne', version_outil='1.0.0')
    # Comme 0.1.69 sur le banc VM : la version d'arrivée du retour n'a pas l'outil
    instance.serveur.sans_outil.add('1.0.0')
    instance.deployer()
    monter(instance, '1.2.0')
    instance.serveur.base['donnees'].append('saisi en 1.2.0')
    shutil.rmtree(instance.racine / 'var/lib/cicada/maintenance/compose/1.0.0')
    instance.serveur.images -= set(images_de('1.0.0'))
    env = instance.racine / 'var/lib/cicada/.env'
    env.write_text(env.read_text() + 'CICADA_HUB_URL=https://hub.exemple\n')
    assert version_env(instance) == '1.2.0' and instance.serveur.base['schema'] == '1.2.0'
    instance.serveur.appels.clear()
    return sauvegarde.name


def test_retour_a_une_version_plus_ancienne_avec_sa_base(instance, trois_versions):
    with pytest.raises(cm.ErreurMaintenance, match='1.0.0.*--avec-sa-version --oui'):
        instance.revenir_a(trois_versions)
    assert instance.serveur.arrets() == [] and version_env(instance) == '1.2.0'

    t = instance.revenir_a(trois_versions, confirme=True)

    assert t['statut'] == cm.REUSSIE and t['depart'] == '1.2.0' and t['cible'] == '1.0.0'
    assert version_env(instance) == '1.0.0'
    assert instance.serveur.application_en_service() == (True, '1.0.0')
    # La base de la sauvegarde, pas la base de 1.2.0 sous le code de 1.0.0
    assert instance.serveur.base == {'schema': '1.0.0', 'donnees': ['plan A', 'plan B']}
    # Les fichiers compose de 1.0.0, repris de la sauvegarde
    assert all('maintenance/compose/1.0.0' in f for f in instance.serveur.derniers_fichiers)
    assert (instance.racine / 'var/lib/cicada/maintenance/compose/1.0.0/docker-compose.yml').read_text() == '# 1.0.0\n'
    # Configuration actuelle conservée : seule la version change
    assert 'CICADA_HUB_URL=https://hub.exemple' in (instance.racine / 'var/lib/cicada/.env').read_text()
    # État d'avant sauvegardé, résultat publié pour la page de mise à jour
    assert 'avant-retour-1.2.0-vers-1.0.0' in t['sauvegarde']
    assert resultat(instance)['statut'] == 'reussie' and resultat(instance)['cible'] == '1.0.0'
    # Images de la version de départ gardées : défaire le retour sans téléchargement
    assert f'{BACKEND}:1.2.0' in instance.serveur.images


def test_retour_a_une_version_se_defait_par_rollback(instance, trois_versions):
    instance.revenir_a(trois_versions, confirme=True)

    t = instance.revenir(confirme=True)

    assert t['statut'] == cm.RETOUR_FAIT
    assert version_env(instance) == '1.2.0'
    assert instance.serveur.application_en_service() == (True, '1.2.0')
    assert 'saisi en 1.2.0' in instance.serveur.base['donnees']
    r = resultat(instance)
    assert r['statut'] == 'retour_demande' and r['origine'] == 'retour_version'


def test_retour_depuis_une_version_sans_l_outil(instance, trois_versions):
    """Instance revenue en 1.0.0 (image sans cicada-db) : un nouveau retour,
    vers une sauvegarde de 1.1.0, se fait avec l'outil du paquet installé."""
    instance.serveur.images |= set(images_de('1.1.0'))
    instance.ecrire_version('1.1.0')
    en_1_1 = instance.sauvegarder('quotidienne-1.1.0').name
    instance.ecrire_version('1.2.0')
    instance.revenir_a(trois_versions, confirme=True)
    assert version_env(instance) == '1.0.0'

    t = instance.revenir_a(en_1_1, confirme=True)

    assert t['statut'] == cm.REUSSIE, t.get('cause')
    assert version_env(instance) == '1.1.0'


def test_apres_un_retour_la_mise_a_jour_se_relance(instance, trois_versions):
    instance.revenir_a(trois_versions, confirme=True)
    assert cm.main_update(['deploy'], instance=instance) == 0  # paquet reconfiguré : relance permise

    assert version_env(instance) == '1.2.0'
    assert instance.serveur.base == {'schema': '1.2.0', 'donnees': ['plan A', 'plan B']}


def test_retour_a_une_version_images_introuvables_rien_ne_change(instance, trois_versions):
    instance.serveur.registre.discard(f'{BACKEND}:1.0.0')

    t = instance.revenir_a(trois_versions, confirme=True)

    assert t['statut'] == cm.ANNULEE and "rien n'a changé" in t['cause']
    assert instance.serveur.arrets() == []
    assert version_env(instance) == '1.2.0' and 'saisi en 1.2.0' in instance.serveur.base['donnees']


def test_retour_a_une_version_restauration_en_echec(instance, trois_versions):
    dossier = instance.dossier_sauvegardes() / trois_versions
    instance.serveur.archives_illisibles.add(str(dossier))

    t = instance.revenir_a(trois_versions, confirme=True)

    assert t['statut'] == cm.RETOUR_FAIT
    assert 'Restauration de la sauvegarde' in t['cause'] and 'retour à la version 1.2.0 effectué' in t['cause']
    assert version_env(instance) == '1.2.0'
    assert instance.serveur.application_en_service() == (True, '1.2.0')
    assert instance.serveur.base['schema'] == '1.2.0' and 'saisi en 1.2.0' in instance.serveur.base['donnees']


def test_retour_a_une_version_qui_ne_demarre_pas(instance, trois_versions):
    instance.serveur.web_casse.add('1.0.0')

    t = instance.revenir_a(trois_versions, confirme=True)

    assert t['statut'] == cm.RETOUR_FAIT
    assert version_env(instance) == '1.2.0'
    assert instance.serveur.application_en_service() == (True, '1.2.0')
    assert instance.serveur.base == {'schema': '1.2.0', 'donnees': ['plan A', 'plan B', 'saisi en 1.2.0']}


def test_retour_a_une_version_interrompu_puis_repris(instance, trois_versions):
    """Serveur coupé pendant le démarrage de 1.0.0 : la reprise remet 1.2.0 et sa base."""
    instance.demarrer = lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        instance.revenir_a(trois_versions, confirme=True)
    del instance.demarrer
    instance.serveur.web_casse.clear()
    assert instance.tentative()['etape'] == 'demarrage'

    t = instance.reprendre()

    assert t['statut'] == cm.RETOUR_FAIT
    assert version_env(instance) == '1.2.0'
    assert 'saisi en 1.2.0' in instance.serveur.base['donnees']


def test_retour_a_une_version_sans_fichiers_de_deploiement_refuse(instance, trois_versions):
    shutil.rmtree(instance.dossier_sauvegardes() / trois_versions / 'compose')

    with pytest.raises(cm.ErreurMaintenance, match='fichiers de déploiement'):
        instance.revenir_a(trois_versions, confirme=True)
    assert instance.serveur.arrets() == [] and version_env(instance) == '1.2.0'


def test_retour_a_une_version_avec_les_fichiers_deposes(instance, trois_versions):
    instance.revenir_a(trois_versions, fichiers=True, confirme=True)

    restaurations = [c for c in instance.serveur.appels if 'restaurer' in c]
    assert '--fichiers' in restaurations[-1]
    # Défaire le retour remet aussi les fichiers d'avant
    instance.revenir(confirme=True)
    restaurations = [c for c in instance.serveur.appels if 'restaurer' in c]
    assert '--fichiers' in restaurations[-1]


def test_cicada_restore_avec_sa_version(instance, trois_versions):
    assert cm.main_restore([trois_versions, '--avec-sa-version'], instance=instance) == 1
    assert cm.main_restore([trois_versions, '--avec-sa-version', '--oui'], instance=instance) == 0
    assert version_env(instance) == '1.0.0'


def test_etat_lisible_sans_l_application(instance):
    instance.serveur.web_casse.add('1.1.0')
    instance.deployer()
    sortie = io.StringIO()

    cm.afficher_etat(instance.etat(), sortie)

    texte = sortie.getvalue()
    assert 'Version du paquet installé : 1.1.0' in texte
    assert 'Version en service         : 1.0.0' in texte
    assert 'sudo cicada-update retry' in texte
    assert 'retour à la version précédente effectué' in texte
    assert 'avant-maj-1.0.0-vers-1.1.0' in texte


def test_codes_de_sortie_de_cicada_update(instance):
    instance.serveur.web_casse.add('1.1.0')
    assert cm.main_update(['deploy'], instance=instance) == 11
    assert cm.main_update(['rollback'], instance=instance) == 1  # déjà revenue
    instance.serveur.web_casse.clear()
    assert cm.main_update(['retry'], instance=instance) == 0
    assert cm.main_update(['status'], instance=instance) == 0


# --- Paquet ------------------------------------------------------------------------

def charger_heartbeat(tmp_path):
    source = (RACINE_PAQUET / 'usr/bin/cicada-heartbeat').read_text()
    source = source.replace('/var/log/cicada-maint/heartbeat.log', str(tmp_path / 'heartbeat.log'))
    spec = importlib.util.spec_from_loader('cicada_heartbeat', loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, 'cicada-heartbeat', 'exec'), module.__dict__)
    return module


def test_heartbeat_annonce_la_version_en_service(tmp_path):
    hb = charger_heartbeat(tmp_path)
    (tmp_path / 'VERSION').write_text('1.1.0\n')
    (tmp_path / '.env').write_text('DB_TYPE=docker\nCICADA_VERSION=1.0.0\n')
    hb.VERSION_FILE, hb.ENV_FILE = str(tmp_path / 'VERSION'), str(tmp_path / '.env')
    assert hb.get_version() == '1.0.0'
    (tmp_path / '.env').unlink()  # avant la première installation : version du paquet
    assert hb.get_version() == '1.1.0'


def test_le_paquet_deroule_la_mise_a_jour_et_ses_services():
    postinst = (RACINE_PAQUET / 'DEBIAN/postinst').read_text()
    assert '/usr/bin/cicada-update deploy' in postinst
    assert 'docker compose' not in postinst  # plus de pull + up -d sans contrôle
    assert 'cicada-backup.timer' in postinst and 'cicada-reprise.service' in postinst
    assert (RACINE_PAQUET / 'DEBIAN/preinst').exists()
    unites = RACINE_PAQUET / 'etc/systemd/system'
    assert 'cicada-update resume' in (unites / 'cicada-reprise.service').read_text()
    assert 'cicada-backup' in (unites / 'cicada-backup.service').read_text()
