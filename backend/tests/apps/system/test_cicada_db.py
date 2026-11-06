"""Sauvegarde et restauration de la base (#796) : `backend/docker/cicada_db.py`.

Sur un vrai PostgreSQL : une base jetable par test, préparée comme le font
`cicada-prepare-db` / `init.sql` (PostGIS, unaccent, schémas au compte de
l'application). Deux comptes : super-utilisateur (base Docker) et simple
propriétaire de la base (PostgreSQL existant, cas de RNF).

Ce qui est vérifié : la restauration remet la base exactement dans l'état de la
sauvegarde (objets créés après retirés, objets supprimés rétablis), et toute
restauration qui échoue — archive tronquée, empreinte fausse, nombre de lignes
différent — laisse la base intacte.
"""
import importlib.util
import json
import os
import pathlib
import shutil
import uuid

import psycopg
import pytest

OUTIL = pathlib.Path(__file__).resolve().parents[3] / 'docker' / 'cicada_db.py'
INIT_SQL = pathlib.Path(__file__).resolve().parents[4] / 'docker' / 'postgres' / 'init.sql'
# Équivalent d'init.sql quand le dépôt n'est pas monté (conteneur de dev : seul
# backend/ l'est) : mêmes extensions et schémas, au compte de l'application.
INIT_MINIMAL = """
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE SCHEMA IF NOT EXISTS utilisateurs;
CREATE SCHEMA IF NOT EXISTS general;
CREATE SCHEMA IF NOT EXISTS taxonomie;
"""

pytestmark = pytest.mark.skipif(
    shutil.which('pg_dump') is None or not os.environ.get('POSTGRES_HOST'),
    reason='client PostgreSQL (pg_dump, pg_restore, psql) absent',
)


def charger_outil():
    spec = importlib.util.spec_from_file_location('cicada_db', OUTIL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cicada_db = charger_outil()

SERVEUR = dict(
    host=os.environ.get('POSTGRES_HOST', 'localhost'),
    port=os.environ.get('POSTGRES_PORT', '5432'),
    user=os.environ.get('POSTGRES_USER', 'postgres'),
    password=os.environ.get('POSTGRES_PASSWORD', ''),
)

CONTENU = """
CREATE TABLE utilisateurs.django_migrations (id serial PRIMARY KEY, app text, name text, applied timestamptz DEFAULT now());
INSERT INTO utilisateurs.django_migrations (app, name)
  SELECT 'plans', lpad(g::text, 4, '0') || '_migration' FROM generate_series(1, 40) g;
CREATE TABLE utilisateurs.t_roles (id serial PRIMARY KEY, email text UNIQUE NOT NULL);
INSERT INTO utilisateurs.t_roles (email) VALUES ('admin@test.fr'), ('user@test.fr');
CREATE TABLE general.t_plan_gestion (
  id_pg serial PRIMARY KEY, nom text NOT NULL, geom geometry(Point, 4326),
  id_redacteur int REFERENCES utilisateurs.t_roles(id));
INSERT INTO general.t_plan_gestion (nom, geom, id_redacteur)
  SELECT format('Plan n°%s — Réserve d''été', g), ST_SetSRID(ST_MakePoint(5 + g / 100.0, 45), 4326), 1
    FROM generate_series(1, 300) g;
CREATE INDEX idx_plan_nom_sans_accents ON general.t_plan_gestion (public.unaccent(nom));
CREATE MATERIALIZED VIEW taxonomie.vm_plans AS SELECT id_pg, upper(nom) AS nom FROM general.t_plan_gestion;
CREATE TEXT SEARCH CONFIGURATION public.french_unaccent (COPY = pg_catalog.french);
ALTER TEXT SEARCH CONFIGURATION public.french_unaccent
  ALTER MAPPING FOR hword, hword_part, word WITH public.unaccent, french_stem;
"""


def connexion_su(base='postgres'):
    return psycopg.connect(dbname=base, autocommit=True, **SERVEUR)


@pytest.fixture
def base(request, monkeypatch):
    """Base jetable préparée comme une installation, contenu de l'application
    créé par son compte. Paramètre : 'super' ou 'proprietaire'."""
    mode = getattr(request, 'param', 'super')
    nom = f'test_sauvegarde_{uuid.uuid4().hex[:10]}'
    role, mdp = SERVEUR['user'], SERVEUR['password']
    with connexion_su() as su:
        if mode == 'proprietaire':
            role, mdp = f'{nom}_app', 'Mdp-App-1'
            su.execute(f'CREATE ROLE {role} LOGIN NOSUPERUSER PASSWORD %s'.replace('%s', f"'{mdp}'"))
        su.execute(f'CREATE DATABASE {nom} OWNER {role} TEMPLATE template0 ENCODING UTF8')
    preparer(nom, role, mdp)
    with psycopg.connect(dbname=nom, autocommit=True, host=SERVEUR['host'], port=SERVEUR['port'],
                         user=role, password=mdp) as app:
        app.execute('ALTER FUNCTION public.unaccent(text) IMMUTABLE')  # comme import_taxref
        app.execute(CONTENU)
    for cle, valeur in (('POSTGRES_DB', nom), ('POSTGRES_USER', role), ('POSTGRES_PASSWORD', mdp)):
        monkeypatch.setenv(cle, valeur)
    yield {'nom': nom, 'role': role, 'mdp': mdp}
    with connexion_su() as su:
        su.execute(f'DROP DATABASE IF EXISTS {nom} WITH (FORCE)')
        if mode == 'proprietaire':
            su.execute(f'DROP ROLE IF EXISTS {role}')


def preparer(nom, role, mdp):
    """Comme cicada-prepare-db : PostGIS en super-utilisateur, init.sql et
    unaccent avec (ou confiés à) le compte de l'application."""
    with connexion_su(nom) as su:
        su.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    with psycopg.connect(dbname=nom, autocommit=True, host=SERVEUR['host'], port=SERVEUR['port'],
                         user=role, password=mdp) as app:
        app.execute(INIT_SQL.read_text() if INIT_SQL.exists() else INIT_MINIMAL)
    with connexion_su(nom) as su:
        su.execute(f'ALTER FUNCTION public.unaccent(text) OWNER TO {role}')


def connexion_app(b):
    return psycopg.connect(dbname=b['nom'], autocommit=True, host=SERVEUR['host'], port=SERVEUR['port'],
                           user=b['role'], password=b['mdp'])


def etat(b):
    """Signature de la base : tables et lignes des schémas de l'application,
    objets de l'application dans public."""
    with connexion_app(b) as c:
        schemas = [r[0] for r in c.execute(cicada_db.SCHEMAS_SQL).fetchall()]
        tables = {}
        for s, t in c.execute(cicada_db.TABLES_SQL, (schemas,)).fetchall():
            tables[f'{s}.{t}'] = c.execute(f'SELECT count(*) FROM "{s}"."{t}"').fetchone()[0]
        colonnes = c.execute(
            "SELECT table_schema || '.' || table_name || '.' || column_name FROM information_schema.columns "
            "WHERE table_schema = ANY(%s) ORDER BY 1", (schemas,)).fetchall()
        public = c.execute(
            "SELECT p.proname FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace "
            "AND pg_get_userbyid(p.proowner) = current_user AND NOT EXISTS (SELECT 1 FROM pg_depend d "
            "WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e') ORDER BY 1").fetchall()
        configs = c.execute("SELECT cfgname FROM pg_ts_config WHERE cfgnamespace = 'public'::regnamespace "
                            "ORDER BY 1").fetchall()
        vue = c.execute('SELECT count(*) FROM taxonomie.vm_plans').fetchone()[0] \
            if 'taxonomie.vm_plans' in [f'{s}.{t}' for s, t in c.execute(
                "SELECT schemaname, matviewname FROM pg_matviews").fetchall()] else None
        accents = c.execute("SELECT count(*) FROM general.t_plan_gestion "
                            "WHERE public.unaccent(nom) LIKE '%Reserve d''ete'").fetchone()[0] \
            if 'general.t_plan_gestion' in tables else None
    return {'schemas': schemas, 'tables': tables, 'colonnes': colonnes, 'public': public,
            'configs': configs, 'vue': vue, 'accents': accents}


def degrader(b):
    """Ce que laisse une mise à jour ratée : migrations à moitié passées."""
    with connexion_app(b) as c:
        c.execute("""
            CREATE TABLE general.t_nouvelle (id int PRIMARY KEY, id_pg int REFERENCES general.t_plan_gestion);
            ALTER TABLE general.t_plan_gestion ADD COLUMN nouvelle_colonne text;
            CREATE SCHEMA ccd_nouveau; CREATE TABLE ccd_nouveau.t (id int);
            DELETE FROM utilisateurs.django_migrations WHERE id > 35;
            UPDATE general.t_plan_gestion SET nom = 'modifié';
            DROP MATERIALIZED VIEW taxonomie.vm_plans;
            CREATE FUNCTION public.fonction_nouvelle() RETURNS int LANGUAGE sql AS 'SELECT 1';
            CREATE TEXT SEARCH CONFIGURATION public.config_nouvelle (COPY = pg_catalog.french);
            DROP TABLE utilisateurs.t_roles CASCADE;
        """)


def lancer(capsys, *args):
    code = cicada_db.main(list(args))
    sortie = capsys.readouterr()
    resultat = json.loads(sortie.out.strip().splitlines()[-1])
    return code, resultat, sortie.err


@pytest.mark.parametrize('base', ['super', 'proprietaire'], indirect=True)
def test_restauration_remet_la_base_dans_l_etat_de_la_sauvegarde(base, tmp_path, capsys):
    reference = etat(base)
    code, resultat, _ = lancer(capsys, 'sauvegarder', str(tmp_path))
    assert code == 0, resultat
    assert resultat['base']['lignes'] == sum(reference['tables'].values())
    manifeste = json.loads((tmp_path / 'base.json').read_text())
    assert manifeste['tables']['general.t_plan_gestion'] == 300
    assert manifeste['migrations'] == {'plans': '0040_migration'}

    degrader(base)
    assert etat(base) != reference

    code, resultat, err = lancer(capsys, 'restaurer', str(tmp_path))
    assert code == 0, err
    assert etat(base) == reference


@pytest.mark.parametrize('base', ['proprietaire'], indirect=True)
def test_restauration_dans_une_base_neuve(base, tmp_path, capsys):
    """Base perdue : recréée vide par cicada-prepare-db, puis restaurée. unaccent()
    n'y est pas encore IMMUTABLE, ce qu'exige l'index sans accents."""
    reference = etat(base)
    assert lancer(capsys, 'sauvegarder', str(tmp_path))[0] == 0
    with connexion_su() as su:
        su.execute(f"DROP DATABASE {base['nom']} WITH (FORCE)")
        su.execute(f"CREATE DATABASE {base['nom']} OWNER {base['role']} TEMPLATE template0 ENCODING UTF8")
    preparer(base['nom'], base['role'], base['mdp'])

    code, _, err = lancer(capsys, 'restaurer', str(tmp_path))
    assert code == 0, err
    assert etat(base) == reference


@pytest.mark.parametrize('base', ['proprietaire'], indirect=True)
def test_archive_tronquee_ne_change_rien(base, tmp_path, capsys):
    assert lancer(capsys, 'sauvegarder', str(tmp_path))[0] == 0
    degrader(base)
    avant = etat(base)
    archive = tmp_path / 'base.dump'
    archive.write_bytes(archive.read_bytes()[: archive.stat().st_size * 2 // 3])
    # Empreinte recalculée : seule la lecture de l'archive peut révéler le défaut
    manifeste = json.loads((tmp_path / 'base.json').read_text())
    manifeste['sha256'] = cicada_db.sha256(str(archive))
    (tmp_path / 'base.json').write_text(json.dumps(manifeste))

    code, resultat, _ = lancer(capsys, 'restaurer', str(tmp_path))
    assert code == 1
    assert 'illisible' in resultat['erreur'] or "n'a pas été modifiée" in resultat['erreur']
    assert etat(base) == avant


@pytest.mark.parametrize('base', ['proprietaire'], indirect=True)
def test_empreinte_differente_refusee_avant_toute_ecriture(base, tmp_path, capsys):
    assert lancer(capsys, 'sauvegarder', str(tmp_path))[0] == 0
    degrader(base)
    avant = etat(base)
    with open(tmp_path / 'base.dump', 'ab') as f:
        f.write(b'\0')

    code, resultat, _ = lancer(capsys, 'restaurer', str(tmp_path))
    assert code == 1
    assert 'Empreinte' in resultat['erreur']
    assert etat(base) == avant
    assert lancer(capsys, 'verifier', str(tmp_path))[0] == 1


@pytest.mark.parametrize('base', ['proprietaire'], indirect=True)
def test_ecart_de_lignes_annule_la_restauration(base, tmp_path, capsys):
    """Le contrôle du nombre de lignes est joué AVANT le COMMIT."""
    assert lancer(capsys, 'sauvegarder', str(tmp_path))[0] == 0
    degrader(base)
    avant = etat(base)
    manifeste = json.loads((tmp_path / 'base.json').read_text())
    manifeste['tables']['general.t_plan_gestion'] += 1
    (tmp_path / 'base.json').write_text(json.dumps(manifeste))

    code, resultat, _ = lancer(capsys, 'restaurer', str(tmp_path))
    assert code == 1
    assert 't_plan_gestion' in resultat['erreur']
    assert etat(base) == avant


@pytest.mark.parametrize('base', ['super'], indirect=True)
def test_fichiers_deposes_sauvegardes_et_restaures(base, tmp_path, capsys):
    media = tmp_path / 'media'
    (media / 'plans' / '42').mkdir(parents=True)
    (media / 'plans' / '42' / 'arrêté.pdf').write_bytes(b'%PDF-1.4 contenu')
    (media / 'logo.png').write_bytes(b'\x89PNG')
    sauvegarde = tmp_path / 'sauvegarde'
    code, resultat, _ = lancer(capsys, 'sauvegarder', str(sauvegarde), '--fichiers', str(media))
    assert code == 0
    assert resultat['fichiers']['nombre'] == 2

    (media / 'logo.png').unlink()
    (media / 'ajout.txt').write_text('déposé après la sauvegarde')
    code, _, err = lancer(capsys, 'restaurer', str(sauvegarde), '--fichiers', str(media))
    assert code == 0, err
    assert sorted(str(p.relative_to(media)) for p in media.rglob('*') if p.is_file()) == \
        ['logo.png', 'plans/42/arrêté.pdf']
    assert (media / 'plans' / '42' / 'arrêté.pdf').read_bytes() == b'%PDF-1.4 contenu'


def test_sans_variables_de_connexion(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv('POSTGRES_DB', raising=False)
    code, resultat, _ = lancer(capsys, 'sauvegarder', str(tmp_path))
    assert code == 1
    assert 'POSTGRES_DB' in resultat['erreur']
    assert not (tmp_path / 'base.dump').exists()
