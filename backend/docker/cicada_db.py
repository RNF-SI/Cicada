#!/usr/bin/env python3
"""cicada-db — sauvegarde et restauration de la base de CICADA (#796).

Installé dans l'image backend (/usr/local/bin/cicada-db) et lancé par les
commandes du serveur (cicada-backup, cicada-restore, cicada-update) dans un
conteneur ponctuel du service `web` : mêmes identifiants (POSTGRES_*), même
réseau que l'application. C'est donc **la base que l'application utilise** qui
est sauvegardée, qu'elle soit dans Docker ou sur un PostgreSQL existant.

Volontairement indépendant de Django : il doit fonctionner quand le code de
l'application ne démarre plus (c'est précisément là qu'on en a besoin).

    cicada-db sauvegarder DOSSIER [--fichiers /app/media]
    cicada-db verifier    DOSSIER
    cicada-db restaurer   DOSSIER [--fichiers /app/media]
    cicada-db version

Sauvegarde : `pg_dump` des schémas de l'application (+ les objets de
l'application dans `public`), dans un instantané de la base dont on tire aussi
le nombre de lignes de chaque table. Le fichier est relu en entier et son
empreinte notée dans `base.json`.

Restauration : **tout ou rien**, dans une seule transaction, avec le compte de
l'application (aucun super-utilisateur : elle marche aussi sur une base
existante dont l'application n'est que propriétaire). Les schémas de
l'application sont supprimés puis recréés depuis l'archive, et le nombre de
lignes de chaque table est comparé à celui de la sauvegarde **avant** le COMMIT.
Une archive abîmée, un manque de droits ou un écart laissent la base intacte.

Sortie : messages lisibles sur stderr, une ligne JSON de résultat sur stdout.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

VERSION_OUTIL = 1

FICHIER_BASE = 'base.dump'
MANIFESTE_BASE = 'base.json'
FICHIER_FICHIERS = 'fichiers.tar.gz'
MANIFESTE_FICHIERS = 'fichiers.json'

# Schémas de l'application : au compte de l'application, hors système, hors
# `public` (partagé avec les extensions) et hors schémas d'extension (tiger,
# topology…), qu'un compte simple ne peut ni supprimer ni recréer.
SCHEMAS_SQL = """
SELECT n.nspname FROM pg_namespace n
 WHERE n.nspname !~ '^pg_' AND n.nspname NOT IN ('information_schema', 'public')
   AND pg_get_userbyid(n.nspowner) = current_user
   AND NOT EXISTS (SELECT 1 FROM pg_extension e WHERE e.extnamespace = n.oid)
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_namespace'::regclass AND d.objid = n.oid AND d.deptype = 'e')
 ORDER BY 1
"""

TABLES_SQL = """
SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p') AND n.nspname = ANY(%s)
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
 ORDER BY 1, 2
"""

# Début de la restauration, joué dans la transaction : vide les schémas de
# l'application et les objets qu'elle possède dans `public` (configuration de
# recherche french_unaccent…), sans toucher aux extensions.
PRELUDE = r"""
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '60s';
DO $cicada_nettoyage$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT n.nspname FROM pg_namespace n
     WHERE n.nspname !~ '^pg_' AND n.nspname NOT IN ('information_schema', 'public')
       AND pg_get_userbyid(n.nspowner) = current_user
       AND NOT EXISTS (SELECT 1 FROM pg_extension e WHERE e.extnamespace = n.oid)
       AND NOT EXISTS (SELECT 1 FROM pg_depend d
                        WHERE d.classid = 'pg_namespace'::regclass AND d.objid = n.oid AND d.deptype = 'e')
  LOOP
    EXECUTE format('DROP SCHEMA %I CASCADE', r.nspname);
  END LOOP;
  FOR r IN
    SELECT (pg_identify_object(o.classid, o.objid, 0)).type AS type,
           (pg_identify_object(o.classid, o.objid, 0)).identity AS identity
      FROM (
        SELECT 'pg_class'::regclass::oid AS classid, c.oid AS objid, c.relowner AS owner, 1 AS ordre
          FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r','p','v','m','S','f')
        UNION ALL
        SELECT 'pg_proc'::regclass::oid, p.oid, p.proowner, 2 FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace
        UNION ALL
        SELECT 'pg_ts_config'::regclass::oid, c.oid, c.cfgowner, 3 FROM pg_ts_config c WHERE c.cfgnamespace = 'public'::regnamespace
        UNION ALL
        SELECT 'pg_ts_dict'::regclass::oid, d.oid, d.dictowner, 4 FROM pg_ts_dict d WHERE d.dictnamespace = 'public'::regnamespace
        UNION ALL
        SELECT 'pg_type'::regclass::oid, t.oid, t.typowner, 5 FROM pg_type t
         WHERE t.typnamespace = 'public'::regnamespace AND t.typtype IN ('e','d','r')
      ) o
     WHERE pg_get_userbyid(o.owner) = current_user
       AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = o.classid AND d.objid = o.objid AND d.deptype = 'e')
     ORDER BY o.ordre
  LOOP
    EXECUTE format('DROP %s IF EXISTS %s CASCADE', r.type, r.identity);
  END LOOP;
END
$cicada_nettoyage$;
-- Les index sans accents (TaxRef, HabRef, CAMPanule) exigent unaccent()
-- IMMUTABLE ; une base neuve ne l'a pas encore. Sans droit, l'erreur de
-- l'index dira laquelle.
DO $cicada_unaccent$
BEGIN
  ALTER FUNCTION public.unaccent(text) IMMUTABLE;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'unaccent() non modifiable : %', SQLERRM;
END
$cicada_unaccent$;
"""

# Entrées de l'archive à ne pas rejouer : le schéma public existe toujours
# (et n'appartient pas à l'application), la table de référence de PostGIS est
# fournie par l'extension et refusée à un compte simple.
TOC_EXCLUE = re.compile(r'^\d+; \d+ \d+ (SCHEMA - public |TABLE DATA public spatial_ref_sys )')


class Erreur(Exception):
    """Échec expliqué : affiché tel quel à l'administrateur."""


def info(message):
    print(message, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Connexion : celle de l'application
# ---------------------------------------------------------------------------

def parametres():
    """Paramètres libpq tirés des variables de l'application (POSTGRES_*)."""
    manquantes = [v for v in ('POSTGRES_DB', 'POSTGRES_USER') if not os.environ.get(v)]
    if manquantes:
        raise Erreur(f"Variables absentes : {', '.join(manquantes)} (à lancer dans le conteneur de l'application)")
    env = dict(os.environ)
    env.update({
        'PGHOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PGPORT': os.environ.get('POSTGRES_PORT', '5432'),
        'PGDATABASE': os.environ['POSTGRES_DB'],
        'PGUSER': os.environ['POSTGRES_USER'],
        'PGPASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'PGAPPNAME': 'cicada-db',
        'PGCONNECT_TIMEOUT': '15',
    })
    # Même chiffrement que l'application (pg_dump / pg_restore le lisent aussi).
    if os.environ.get('POSTGRES_SSLMODE'):
        env['PGSSLMODE'] = os.environ['POSTGRES_SSLMODE']
    return env


def connecter(env):
    import psycopg
    try:
        return psycopg.connect(
            host=env['PGHOST'], port=env['PGPORT'], dbname=env['PGDATABASE'], user=env['PGUSER'],
            password=env['PGPASSWORD'], application_name='cicada-db', connect_timeout=15,
            autocommit=True,
        )
    except psycopg.Error as e:
        raise Erreur(f"Connexion à la base {env['PGDATABASE']} sur {env['PGHOST']}:{env['PGPORT']} impossible : {e}")


def version_serveur(conn):
    num = int(conn.execute('SHOW server_version_num').fetchone()[0])
    return num // 10000, conn.execute('SHOW server_version').fetchone()[0].split()[0]


def outil(nom, major):
    """Binaire PostgreSQL de la version majeure du serveur, sinon le plus
    récent disponible s'il la couvre. pg_dump refuse un serveur plus récent que
    lui ; une sortie d'une version plus récente que le serveur peut contenir des
    réglages qu'il ne connaît pas : on prend la même version quand elle existe."""
    candidats = [f'/usr/lib/postgresql/{major}/bin/{nom}']
    racine = '/usr/lib/postgresql'
    if os.path.isdir(racine):
        for v in sorted((d for d in os.listdir(racine) if d.isdigit()), key=int, reverse=True):
            if int(v) >= major:
                candidats.append(f'{racine}/{v}/bin/{nom}')
    trouve = shutil.which(nom)
    if trouve:
        candidats.append(trouve)
    for chemin in candidats:
        if os.path.isfile(chemin) and os.access(chemin, os.X_OK):
            sortie = subprocess.run([chemin, '--version'], capture_output=True, text=True).stdout
            m = re.search(r'(\d+)(?:\.\d+)?', sortie)
            if m and int(m.group(1)) >= major:
                return chemin
    raise Erreur(f"{nom} pour PostgreSQL {major} introuvable dans l'image : serveur trop récent pour cet outil")


# ---------------------------------------------------------------------------
# Empreintes et manifestes
# ---------------------------------------------------------------------------

def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, 'rb') as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloc)
    return h.hexdigest()


def ecrire_json(chemin, donnees):
    tmp = chemin + '.partiel'
    with open(tmp, 'w') as f:
        json.dump(donnees, f, indent=1, ensure_ascii=False)
    os.replace(tmp, chemin)


def lire_json(chemin):
    try:
        with open(chemin) as f:
            return json.load(f)
    except FileNotFoundError:
        raise Erreur(f"{os.path.basename(chemin)} absent : sauvegarde incomplète")
    except ValueError:
        raise Erreur(f"{os.path.basename(chemin)} illisible : sauvegarde abîmée")


def maintenant():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def ident(*parties):
    return '.'.join('"' + p.replace('"', '""') + '"' for p in parties)


# ---------------------------------------------------------------------------
# Sauvegarde
# ---------------------------------------------------------------------------

def sauvegarder(dossier, fichiers=None):
    env = parametres()
    os.makedirs(dossier, exist_ok=True)
    conn = connecter(env)
    major, version = version_serveur(conn)
    pg_dump = outil('pg_dump', major)
    pg_restore = outil('pg_restore', major)

    # Un seul instantané pour le dump et le comptage des lignes : sans lui, une
    # sauvegarde faite application en marche (quotidienne) ne pourrait pas
    # être vérifiée à la restauration.
    conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
    instantane = conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
    schemas = [r[0] for r in conn.execute(SCHEMAS_SQL).fetchall()]
    if not schemas:
        raise Erreur(f"Aucun schéma de l'application dans {env['PGDATABASE']} (compte {env['PGUSER']})")

    cible = os.path.join(dossier, FICHIER_BASE)
    partiel = cible + '.partiel'
    info(f"Sauvegarde de la base {env['PGDATABASE']} ({env['PGHOST']}:{env['PGPORT']}, PostgreSQL {version}), "
         f"{len(schemas)} schémas…")
    cmd = [pg_dump, '-Fc', '--no-password', f'--snapshot={instantane}', '-f', partiel,
           '--exclude-table-data=public.spatial_ref_sys', '-n', 'public']
    for s in schemas:
        cmd += ['-n', s]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        _supprimer(partiel)
        raise Erreur(f"pg_dump a échoué : {(r.stderr or r.stdout).strip()[-800:]}")

    tables = {}
    for schema, table in conn.execute(TABLES_SQL, (schemas,)).fetchall():
        tables[f'{schema}.{table}'] = conn.execute(f'SELECT count(*) FROM {ident(schema, table)}').fetchone()[0]
    migrations = _dernieres_migrations(conn, schemas)
    conn.execute('ROLLBACK')
    conn.close()

    # Relecture complète : une archive qui ne se relit pas ne sert à rien.
    r = subprocess.run([pg_restore, '-f', os.devnull, partiel], capture_output=True, text=True)
    if r.returncode != 0:
        _supprimer(partiel)
        raise Erreur(f"Archive produite illisible : {(r.stderr or r.stdout).strip()[-800:]}")
    os.replace(partiel, cible)
    manifeste = {
        'outil': VERSION_OUTIL,
        'date': maintenant(),
        'base': env['PGDATABASE'],
        'hote': f"{env['PGHOST']}:{env['PGPORT']}",
        'compte': env['PGUSER'],
        'postgresql': version,
        'postgresql_majeure': major,
        'schemas': schemas,
        'fichier': FICHIER_BASE,
        'taille': os.path.getsize(cible),
        'sha256': sha256(cible),
        'lignes': sum(tables.values()),
        'tables': tables,
        'migrations': migrations,
    }
    ecrire_json(os.path.join(dossier, MANIFESTE_BASE), manifeste)
    info(f"  base : {manifeste['taille'] // 1024} Kio, {len(tables)} tables, {manifeste['lignes']} lignes, relue en entier")

    resultat = {'base': _resume(manifeste)}
    if fichiers:
        resultat['fichiers'] = sauvegarder_fichiers(dossier, fichiers)
    return resultat


def _dernieres_migrations(conn, schemas):
    """Dernière migration appliquée de chaque application Django (diagnostic :
    dit de quelle version de CICADA vient la sauvegarde)."""
    if 'utilisateurs' not in schemas:
        return {}
    existe = conn.execute("SELECT to_regclass('utilisateurs.django_migrations')").fetchone()[0]
    if not existe:
        return {}
    lignes = conn.execute('SELECT app, max(name) FROM utilisateurs.django_migrations GROUP BY app ORDER BY app').fetchall()
    return {app: nom for app, nom in lignes}


def sauvegarder_fichiers(dossier, racine):
    if not os.path.isdir(racine):
        raise Erreur(f"Dossier des fichiers déposés introuvable : {racine}")
    cible = os.path.join(dossier, FICHIER_FICHIERS)
    partiel = cible + '.partiel'
    nombre = 0
    with tarfile.open(partiel, 'w:gz') as tar:
        for nom in sorted(os.listdir(racine)):
            if nom.startswith('.restauration'):
                continue
            tar.add(os.path.join(racine, nom), arcname=nom)
    with tarfile.open(partiel, 'r:gz') as tar:  # relecture complète
        for membre in tar:
            if membre.isfile():
                nombre += 1
                tar.extractfile(membre).read()
    os.replace(partiel, cible)
    manifeste = {'outil': VERSION_OUTIL, 'date': maintenant(), 'fichier': FICHIER_FICHIERS,
                 'taille': os.path.getsize(cible), 'sha256': sha256(cible), 'nombre': nombre}
    ecrire_json(os.path.join(dossier, MANIFESTE_FICHIERS), manifeste)
    info(f"  fichiers déposés : {nombre} fichiers, {manifeste['taille'] // 1024} Kio")
    return {k: manifeste[k] for k in ('taille', 'sha256', 'nombre')}


def _supprimer(chemin):
    try:
        os.remove(chemin)
    except FileNotFoundError:
        pass


def _resume(m):
    return {k: m[k] for k in ('date', 'base', 'hote', 'postgresql', 'taille', 'sha256', 'lignes', 'migrations')}


# ---------------------------------------------------------------------------
# Vérification
# ---------------------------------------------------------------------------

def verifier(dossier, avec_fichiers=None):
    """Empreinte + relecture complète. avec_fichiers=None : les fichiers
    déposés sont vérifiés s'ils sont dans la sauvegarde."""
    manifeste = lire_json(os.path.join(dossier, MANIFESTE_BASE))
    archive = os.path.join(dossier, manifeste.get('fichier', FICHIER_BASE))
    if not os.path.isfile(archive):
        raise Erreur(f"{os.path.basename(archive)} absent : sauvegarde incomplète")
    if sha256(archive) != manifeste.get('sha256'):
        raise Erreur("Empreinte de la base différente de celle notée à la sauvegarde : fichier abîmé ou modifié")
    pg_restore = outil('pg_restore', int(manifeste.get('postgresql_majeure') or 0))
    r = subprocess.run([pg_restore, '-f', os.devnull, archive], capture_output=True, text=True)
    if r.returncode != 0:
        raise Erreur(f"Archive de la base illisible : {(r.stderr or r.stdout).strip()[-800:]}")
    resultat = {'base': _resume(manifeste)}
    chemin_f = os.path.join(dossier, MANIFESTE_FICHIERS)
    if avec_fichiers or (avec_fichiers is None and os.path.exists(chemin_f)):
        mf = lire_json(chemin_f)
        archive_f = os.path.join(dossier, mf.get('fichier', FICHIER_FICHIERS))
        if not os.path.isfile(archive_f) or sha256(archive_f) != mf.get('sha256'):
            raise Erreur("Archive des fichiers déposés absente ou abîmée (empreinte différente)")
        resultat['fichiers'] = {k: mf[k] for k in ('taille', 'sha256', 'nombre')}
    return resultat


# ---------------------------------------------------------------------------
# Restauration
# ---------------------------------------------------------------------------

def restaurer(dossier, fichiers=None):
    env = parametres()
    verifier(dossier, avec_fichiers=bool(fichiers))
    manifeste = lire_json(os.path.join(dossier, MANIFESTE_BASE))
    archive = os.path.join(dossier, manifeste.get('fichier', FICHIER_BASE))

    conn = connecter(env)
    major, version = version_serveur(conn)
    conn.close()
    if major != manifeste.get('postgresql_majeure'):
        info(f"  ! sauvegarde faite sous PostgreSQL {manifeste.get('postgresql')}, serveur actuel {version}")
    pg_restore = outil('pg_restore', major)
    psql = outil('psql', major)

    toc = subprocess.run([pg_restore, '-l', archive], capture_output=True, text=True)
    if toc.returncode != 0:
        raise Erreur(f"Sommaire de l'archive illisible : {toc.stderr.strip()[-500:]}")
    with tempfile.NamedTemporaryFile('w', suffix='.list', delete=False) as f:
        f.write(''.join(l + '\n' for l in toc.stdout.splitlines() if not TOC_EXCLUE.match(l)))
        liste = f.name

    info(f"Restauration de {env['PGDATABASE']} ({env['PGHOST']}:{env['PGPORT']}) depuis la sauvegarde "
         f"du {manifeste.get('date')} — tout ou rien…")
    erreurs = tempfile.TemporaryFile('w+')
    try:
        p_psql = subprocess.Popen([psql, '-X', '-q', '--no-password', '-v', 'ON_ERROR_STOP=1', '-f', '-'],
                                  stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=erreurs, env=env)
        p_rest = subprocess.Popen([pg_restore, '-L', liste, '--clean', '--if-exists', '--no-owner',
                                   '--no-acl', '-f', '-', archive],
                                  stdout=subprocess.PIPE, stderr=erreurs)
        coupe = False
        try:
            p_psql.stdin.write(PRELUDE.encode())
            for bloc in iter(lambda: p_rest.stdout.read(1024 * 1024), b''):
                p_psql.stdin.write(bloc)
        except BrokenPipeError:
            coupe = True  # psql s'est arrêté sur une erreur : rien n'est validé
        # Fermé avant d'attendre : si psql s'est arrêté, pg_restore ne doit pas
        # rester bloqué sur un tuyau que plus personne ne lit.
        p_rest.stdout.close()
        rc_rest = p_rest.wait()
        if not coupe:
            fin = _controle_lignes(manifeste['tables']) + 'COMMIT;\n' if rc_rest == 0 else 'ROLLBACK;\n'
            try:
                p_psql.stdin.write(fin.encode())
            except BrokenPipeError:
                pass
        try:
            p_psql.stdin.close()
        except BrokenPipeError:
            pass
        rc_psql = p_psql.wait()
        erreurs.seek(0)
        journal = erreurs.read()
    finally:
        erreurs.close()
        os.unlink(liste)

    if rc_rest != 0 or rc_psql != 0:
        lignes = [l for l in journal.splitlines() if re.search(r'ERR|FATAL|error', l)]
        raise Erreur("Restauration annulée, la base n'a pas été modifiée : "
                     + ('\n'.join(lignes[-6:]) or journal.strip()[-800:] or f'code {rc_psql}'))

    # Statistiques à jour : sans elles, les requêtes à jointures profondes
    # deviennent très lentes juste après la restauration.
    subprocess.run([psql, '-X', '-q', '--no-password', '-c', 'ANALYZE'], env=env, capture_output=True)
    info(f"  base restaurée : {len(manifeste['tables'])} tables, {manifeste.get('lignes')} lignes, contrôlées")
    resultat = {'base': _resume(manifeste)}
    if fichiers:
        resultat['fichiers'] = restaurer_fichiers(dossier, fichiers)
    return resultat


def _controle_lignes(tables):
    """Bloc SQL, joué avant le COMMIT, qui annule tout si une table n'a pas le
    nombre de lignes noté à la sauvegarde."""
    tests = []
    for nom, attendu in sorted(tables.items()):
        schema, table = nom.split('.', 1)
        tests.append(f"  IF (SELECT count(*) FROM {ident(schema, table)}) <> {int(attendu)} THEN "
                     f"RAISE EXCEPTION 'Contrôle après restauration : {nom.replace(chr(39), chr(39) * 2)} "
                     f"n''a pas {int(attendu)} lignes'; END IF;\n")
    return 'DO $cicada_controle$\nBEGIN\n' + ''.join(tests) + 'END\n$cicada_controle$;\n'


def restaurer_fichiers(dossier, racine):
    mf = lire_json(os.path.join(dossier, MANIFESTE_FICHIERS))
    archive = os.path.join(dossier, mf.get('fichier', FICHIER_FICHIERS))
    if not os.path.isdir(racine):
        raise Erreur(f"Dossier des fichiers déposés introuvable : {racine}")
    # Extraction à côté, puis remplacement : une archive qui casse en route
    # laisse les fichiers actuels en place.
    temp = os.path.join(racine, '.restauration')
    shutil.rmtree(temp, ignore_errors=True)
    os.makedirs(temp)
    with tarfile.open(archive, 'r:gz') as tar:
        tar.extractall(temp, filter='data')
    for nom in os.listdir(racine):
        if nom == '.restauration':
            continue
        chemin = os.path.join(racine, nom)
        if os.path.isdir(chemin) and not os.path.islink(chemin):
            shutil.rmtree(chemin)
        else:
            os.remove(chemin)
    for nom in os.listdir(temp):
        os.rename(os.path.join(temp, nom), os.path.join(racine, nom))
    os.rmdir(temp)
    info(f"  fichiers déposés restaurés : {mf.get('nombre')} fichiers")
    return {k: mf[k] for k in ('taille', 'sha256', 'nombre')}


# ---------------------------------------------------------------------------

def main(argv=None):
    os.umask(0o077)  # sauvegarde lisible par son propriétaire seul
    parser = argparse.ArgumentParser(prog='cicada-db', description=__doc__.split('\n\n')[0])
    sous = parser.add_subparsers(dest='action', required=True)
    for nom in ('sauvegarder', 'restaurer'):
        p = sous.add_parser(nom)
        p.add_argument('dossier')
        p.add_argument('--fichiers', help='dossier des fichiers déposés (ex. /app/media)')
    sous.add_parser('verifier').add_argument('dossier')
    sous.add_parser('version')
    args = parser.parse_args(argv)
    try:
        if args.action == 'version':
            resultat = {'outil': VERSION_OUTIL}
        elif args.action == 'sauvegarder':
            resultat = sauvegarder(args.dossier, args.fichiers)
        elif args.action == 'verifier':
            resultat = verifier(args.dossier)
        else:
            resultat = restaurer(args.dossier, args.fichiers)
    except Erreur as e:
        info(f"ÉCHEC : {e}")
        print(json.dumps({'ok': False, 'erreur': str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps({'ok': True, **resultat}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
