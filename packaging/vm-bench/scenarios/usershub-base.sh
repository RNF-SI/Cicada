# DESCRIPTION: Connexion par la base UsersHub (#764) : GeoNature et sa base sur le même serveur que CICADA, compte de lecture créé par cicada-usershub-lecture --docker-local, test du formulaire, puis connexions réelles (droit CICADA via un groupe, md5, droit GeoNature seul, aucun droit, compte désactivé)
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Topologie de Maxime (GeoNature et UsersHub sur le serveur CICADA, PostgreSQL
# hors Docker) : la base UsersHub est jointe par les conteneurs via
# host.docker.internal. La base de CICADA reste dans son conteneur.
#
# Les connexions demandent un backend qui connaît la source « base » : tant
# que la version n'est pas publiée, passer l'image construite en local
#   docker build -f backend/Dockerfile.prod -t cicada-backend:local backend
#   docker save cicada-backend:local -o /tmp/backend.tar
#   ./bench.sh run usershub-base --backend-image /tmp/backend.tar
# Elle est chargée APRÈS l'installation, comme une mise à jour de l'image sur
# une instance en service (le formulaire a déjà écrit le .env).

. "$BENCH_DIR/guest/prereq-postgres.sh"

UH_DB="geonature2db"
UH_PASSWORD="pas-encore-connu"
LOCAL_LOGIN=closed
UH_PASS_TEST="Mdp-UsersHub-1"

scenario_prereqs() {
    install_host_postgres || return 1
    pg "CREATE ROLE geonatadmin LOGIN PASSWORD 'gn-pass'"
    pg "CREATE DATABASE $UH_DB OWNER geonatadmin"
    # Schéma UsersHub réduit, avec des colonnes que le compte de lecture ne
    # doit PAS lire (api_key, remarques, date_insert).
    sudo -u postgres psql -v ON_ERROR_STOP=1 -q -d "$UH_DB" <<SQL
CREATE EXTENSION pgcrypto;
CREATE SCHEMA utilisateurs AUTHORIZATION geonatadmin;
CREATE TABLE utilisateurs.t_applications (id_application int PRIMARY KEY, code_application text, nom_application text);
CREATE TABLE utilisateurs.bib_organismes (id_organisme int PRIMARY KEY, uuid_organisme uuid, nom_organisme text,
    adresse_organisme text, cp_organisme text, ville_organisme text, tel_organisme text, fax_organisme text,
    email_organisme text, url_organisme text, id_parent int);
CREATE TABLE utilisateurs.t_roles (id_role int PRIMARY KEY, groupe boolean DEFAULT false, identifiant text,
    email text, nom_role text, prenom_role text, id_organisme int, pass text, pass_plus text,
    active boolean DEFAULT true, api_key text, remarques text, date_insert timestamp DEFAULT now());
CREATE TABLE utilisateurs.cor_roles (id_role_groupe int, id_role_utilisateur int);
CREATE TABLE utilisateurs.cor_role_app_profil (id_role int, id_application int, id_profil int);
INSERT INTO utilisateurs.t_applications VALUES (3, 'GN', 'GeoNature'), (18, 'CICADA', 'Cicada');
INSERT INTO utilisateurs.bib_organismes (id_organisme, uuid_organisme, nom_organisme, ville_organisme)
    VALUES (7, '6c7a3b0e-0d1f-4a8e-9a55-2f7f2b1f1001', 'Réserve du banc', 'Dijon');
INSERT INTO utilisateurs.t_roles (id_role, groupe, nom_role) VALUES (900, true, 'Grp_cicada'), (901, true, 'Grp_gn');
INSERT INTO utilisateurs.cor_role_app_profil VALUES (900, 18, 1), (901, 3, 1);
INSERT INTO utilisateurs.t_roles (id_role, identifiant, email, nom_role, prenom_role, id_organisme, pass, pass_plus, active, api_key) VALUES
    (101, 'uh_groupe',   'uh_groupe@bench.test',   'Groupe',  'Claire', 7, NULL, crypt('$UH_PASS_TEST', gen_salt('bf', 4)), true,  'secret-api'),
    (102, 'uh_md5',      'uh_md5@bench.test',      'Md5',     'Paul',   7, md5('$UH_PASS_TEST'), NULL,                    true,  NULL),
    (103, 'uh_gn',       'uh_gn@bench.test',       'GnSeul',  'Lea',    7, NULL, crypt('$UH_PASS_TEST', gen_salt('bf', 4)), true,  NULL),
    (104, 'uh_rien',     'uh_rien@bench.test',     'Rien',    'Jean',   7, NULL, crypt('$UH_PASS_TEST', gen_salt('bf', 4)), true,  NULL),
    (105, 'uh_inactif',  'uh_inactif@bench.test',  'Inactif', 'Anne',   7, NULL, crypt('$UH_PASS_TEST', gen_salt('bf', 4)), false, NULL);
INSERT INTO utilisateurs.cor_roles VALUES (900, 101), (900, 102), (901, 103), (900, 105);
SQL
}

strip()    { sed 's/\x1b\[[0-9;]*m//g'; }
statuses() { python3 -c "import json,sys;print(' '.join(c['status'] for c in json.load(sys.stdin)['checks']))"; }
labels()   { python3 -c "import json,sys;print(' | '.join(c['label'] for c in json.load(sys.stdin)['checks']))"; }
api_test_usershub() {  # api_test_usershub MOTDEPASSE CODE → JSON des contrôles
    curl -s --max-time 30 -H 'Content-Type: application/json' \
        -d "{\"usershub_db_host\":\"localhost\",\"usershub_db_port\":\"5432\",\"usershub_db_name\":\"$UH_DB\",\"usershub_db_user\":\"cicada_usershub\",\"usershub_db_password\":\"$1\",\"geonature_auth_code_application\":\"$2\"}" \
        http://127.0.0.1:4567/api/test-usershub
}

before_form() {
    local out result
    check "Le formulaire affiche la commande du compte de lecture" bash -c \
        "curl -s http://127.0.0.1:4567/ | grep -q 'id=\"usershub_command\"'"
    check "L'installateur sert cicada-usershub-lecture tel qu'installé" bash -c \
        "curl -s http://127.0.0.1:4567/usershub-lecture.sh | cmp -s - /usr/bin/cicada-usershub-lecture"

    step "Compte de lecture UsersHub (PostgreSQL livré en listen_addresses = 'localhost')"
    out="$(cicada-usershub-lecture --db "$UH_DB" --docker-local 2>&1 | strip)"
    check "Le script refuse et explique listen_addresses" bash -c "echo \"\$1\" | grep -q \"listen_addresses = '\\*'\"" _ "$out"
    sudo -u postgres psql -Atc "ALTER SYSTEM SET listen_addresses = '*'" >/dev/null
    systemctl restart postgresql
    wait_for 30 sudo -u postgres psql -Atc 'select 1'

    if out="$(cicada-usershub-lecture --db "$UH_DB" --docker-local 2>&1 | strip)"; then
        record PASS "cicada-usershub-lecture --docker-local"
    else
        record FAIL "cicada-usershub-lecture --docker-local" "$(echo "$out" | grep -v '^\s*$' | tail -2)"
    fi
    echo "$out"
    check "Le script compte les comptes autorisés sur CICADA (2 actifs)" bash -c "echo \"\$1\" | grep -q '2 compte(s) actif(s)'" _ "$out"
    check "Le script vérifie par l'interface Docker" bash -c "echo \"\$1\" | grep -q 'interface Docker'" _ "$out"
    UH_PASSWORD="$(echo "$out" | awk -F': *' '/Mot de passe  *:/{split($2,a," "); print a[1]; exit}')"
    check "Mot de passe affiché par le script" test -n "$UH_PASSWORD"

    out="$(cicada-usershub-lecture --db "$UH_DB" --docker-local 2>&1 | strip)"
    check "Relancé, le script garde le mot de passe" bash -c "echo \"\$1\" | grep -q 'mot de passe inchangé'" _ "$out"

    for q in "select * from utilisateurs.t_roles" "select api_key from utilisateurs.t_roles" \
             "update utilisateurs.t_roles set active = true"; do
        if PGPASSWORD="$UH_PASSWORD" psql -h 127.0.0.1 -U cicada_usershub -d "$UH_DB" -Atc "$q" >/dev/null 2>&1; then
            record FAIL "Compte de lecture : refus de « $q »" "accepté"
        else
            record PASS "Compte de lecture : refus de « $q »"
        fi
    done

    result="$(api_test_usershub "$UH_PASSWORD" CICADA)"
    if [ "$(echo "$result" | statuses)" = "ok ok ok" ]; then
        record PASS "Test « Tester la base UsersHub » avec « localhost »" "$(echo "$result" | labels)"
    else
        record FAIL "Test « Tester la base UsersHub » avec « localhost »" "$(echo "$result" | labels)"
    fi
    result="$(api_test_usershub "$UH_PASSWORD" ABSENTE)"
    check "Le test signale une application absente" bash -c "echo \"\$1\" | grep -q 'Aucune application'" _ "$result"
    result="$(api_test_usershub faux CICADA)"
    check "Le test signale un mauvais mot de passe" bash -c "echo \"\$1\" | grep -q 'impossible'" _ "$result"
}

scenario_db_answers() {
    cat <<EOF
"db_type": "docker",
  "db_host": "db",
  "db_port": "5432",
  "db_name": "cicada",
  "db_user": "cicada_user",
  "db_password": "Bench-Db-Pass-1",
  "auth_provider": "geonature",
  "geonature_auth_libelle": "Banc",
  "geonature_auth_code_application": "CICADA",
  "usershub_db_host": "localhost",
  "usershub_db_port": "5432",
  "usershub_db_name": "$UH_DB",
  "usershub_db_user": "cicada_usershub",
  "usershub_db_password": "$UH_PASSWORD"
EOF
}

login_uh() {  # login_uh IDENTIFIANT MOTDEPASSE → code HTTP (réponse dans login-uh.json)
    curl -s -o "$BENCH_DIR/login-uh.json" -w '%{http_code}' --max-time 20 \
        -H 'Content-Type: application/json' -H "Host: $DOMAIN" \
        -d "{\"login\":\"$1\",\"password\":\"$2\"}" \
        "http://127.0.0.1:$FRONTEND_PORT/api/auth/login-geonature/"
}

scenario_checks() {
    check "code de l'application dans le .env" grep -qx 'GEONATURE_AUTH_CODE_APPLICATION=CICADA' /var/lib/cicada/.env
    check "USERSHUB_DB_HOST=host.docker.internal dans le .env" grep -qx 'USERSHUB_DB_HOST=host.docker.internal' /var/lib/cicada/.env
    check "Le conteneur web joint la base UsersHub de l'hôte" bash -c \
        "docker exec cicada_prod_web python -c \"
import os, psycopg
psycopg.connect(host=os.environ['USERSHUB_DB_HOST'], port=os.environ['USERSHUB_DB_PORT'], dbname=os.environ['USERSHUB_DB_NAME'],
                user=os.environ['USERSHUB_DB_USER'], password=os.environ['USERSHUB_DB_PASSWORD'], connect_timeout=5).close()\""

    if [ ! -f "$BENCH_DIR/backend-image.tar" ]; then
        if docker exec cicada_prod_web test -f /app/apps/authentication/providers/usershub_base.py; then
            note "Backend publié avec la source « base » : connexions testées sur l'image installée"
        else
            record INFO "Connexions non testées" "image publiée sans #764 : relancer avec --backend-image"
            return 0
        fi
    else
        step "Image backend locale (comme une mise à jour d'image sur une instance en service)"
        local loaded version
        loaded="$(docker load -i "$BENCH_DIR/backend-image.tar" | sed -n 's/^Loaded image: //p' | tail -1)"
        version="$(env_value CICADA_VERSION)"
        docker tag "$loaded" "ghcr.io/rnf-si/cicada-backend:$version"
        # La commande que cicada-usershub-lecture donne aux instances en service
        bash -c '. /usr/share/cicada/compose-files.sh && cd /usr/share/cicada && docker compose $(compose_files_args) --env-file /var/lib/cicada/.env up -d web' >/dev/null 2>&1
        wait_for 300 test "$(container_health cicada_prod_web)" = healthy
        check "web redémarré avec l'image locale ($loaded)" test "$(container_health cicada_prod_web)" = healthy
    fi

    step "Vérification avant bascule (verifier_usershub)"
    local out rc
    out="$(docker exec cicada_prod_web python manage.py verifier_usershub 2>&1)"; rc=$?
    echo "$out" | grep -v DEBUG | tail -6
    # Seul compte CICADA à ce stade : le super-admin du formulaire, sans compte UsersHub
    check "verifier_usershub signale le super-admin sans compte UsersHub (code 1)" bash -c \
        "[ $rc = 1 ] && echo \"\$1\" | grep -q '$ADMIN_EMAIL — aucun compte UsersHub'" _ "$out"

    step "Connexions par la base UsersHub"
    local spec ident code attendu motif
    for spec in "uh_groupe|$UH_PASS_TEST|200|access|droit CICADA via un groupe" \
                "uh_md5|$UH_PASS_TEST|200|access|ancien mot de passe md5" \
                "uh_groupe|faux|401|incorrect|mauvais mot de passe" \
                "inconnu|$UH_PASS_TEST|401|incorrect|identifiant inconnu" \
                "uh_gn|$UH_PASS_TEST|403|pas accès à CICADA|droit GeoNature seulement" \
                "uh_rien|$UH_PASS_TEST|403|pas accès à CICADA|aucun droit" \
                "uh_inactif|$UH_PASS_TEST|403|désactivé|compte désactivé"; do
        IFS='|' read -r ident pass attendu motif label <<< "$spec"
        code="$(login_uh "$ident" "$pass")"
        if [ "$code" = "$attendu" ] && grep -q "$motif" "$BENCH_DIR/login-uh.json"; then
            record PASS "Connexion UsersHub : $label → $attendu"
        else
            record FAIL "Connexion UsersHub : $label → $attendu" "HTTP $code $(head -c 200 "$BENCH_DIR/login-uh.json")"
        fi
    done

    check "Compte CICADA créé et rattaché à son organisme UsersHub" \
        test "$(app_sql "select o.nom_organisme from utilisateurs.t_roles r join utilisateurs.bib_organismes o on o.uuid_organisme = r.uuid_organisme where r.usershub_id_role = 101")" = "Réserve du banc"
    check "Aucun compte CICADA pour les refusés" \
        test "$(app_sql "select count(*) from utilisateurs.t_roles where usershub_id_role in (103, 104, 105)")" = 0
    out="$(docker exec cicada_prod_web python manage.py verifier_usershub 2>&1)"
    check "verifier_usershub compte les comptes créés à la connexion" bash -c \
        "echo \"\$1\" | grep -q '3 compte(s) CICADA actif(s) : 2 pourront se connecter, 1 seraient refusés'" _ "$out"
    check "Rien n'est écrit dans UsersHub (md5 non réécrit)" \
        test -z "$(sudo -u postgres psql -d "$UH_DB" -Atc "select pass_plus from utilisateurs.t_roles where id_role = 102")"
    # Compte de lecture inutilisable (mot de passe changé, NOLOGIN…) : même
    # chemin qu'une base arrêtée côté backend (OperationalError).
    sudo -u postgres psql -Atqc "ALTER ROLE cicada_usershub NOLOGIN"
    code="$(login_uh uh_groupe "$UH_PASS_TEST")"
    sudo -u postgres psql -Atqc "ALTER ROLE cicada_usershub LOGIN"
    if [ "$code" = 502 ]; then
        record PASS "Base UsersHub inaccessible → 502 explicite" "$(head -c 160 "$BENCH_DIR/login-uh.json")"
    else
        record FAIL "Base UsersHub inaccessible → 502 explicite" "HTTP $code $(head -c 200 "$BENCH_DIR/login-uh.json")"
    fi
    check "Connexion rétablie quand le compte de lecture revient" test "$(login_uh uh_groupe "$UH_PASS_TEST")" = 200
}
