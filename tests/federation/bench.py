#!/usr/bin/env python3
"""
Tests du banc d'essai de l'exploration fédérée (#636).

Ils s'exécutent **contre les trois briques réellement lancées** — deux instances
CICADA et le hub — et non contre des doublures. C'est délibéré : tous les bugs
rencontrés au montage de la fédération étaient des bugs de **couture**, et aucun
des 195 tests unitaires ne les a vus.

    identité d'instance vide → 22 plans publiés, 0 document
    facettes lues sur l'index → un plan sans contenu part sans facettes
    deux migrations 0004 → conteneur en boucle de redémarrage
    nom de projet Compose absent → base de l'instance principale détruite

Les deux projets ont été testés chacun contre **sa propre idée** du contrat.
Personne ne les avait fait se parler.

## Ce qui est couvert

- **contrat** : la charge utile que produit CICADA passe la validation du hub ;
- **scénarios** : aller-retour, isolation entre instances, dépublication,
  idempotence, garde-fou d'identité ;
- **parité** : la même recherche sur le même corpus rend le même résultat, que
  l'exploration soit servie par l'index local ou relayée par le hub.

La parité est le test le plus important. `filters.py` existe en deux
exemplaires, un par projet : sans elle, les deux implémentations divergeraient
en silence, et l'utilisateur constaterait la différence sans pouvoir la décrire.

## Exécution

    scripts/federation.sh test --bench

Ils ne sont **pas** en CI : ils demandent trois stacks Docker. Ils ne sont pas
non plus en pytest — l'hôte n'a que `requests`, et déclencher une publication
demande un `docker exec` que l'intérieur d'un conteneur ne peut pas faire.

## Effets de bord

Ces tests **publient** et, pour un cas, dépublient temporairement un plan. Ils
restaurent l'état ensuite, y compris en cas d'échec. Ils ne touchent jamais aux
bases des instances autrement que par le statut d'un plan, remis comme il était.
"""

import json
import os
import subprocess
import sys
import traceback

import requests

RNF_API = os.environ.get('BENCH_RNF_API', 'http://localhost:8000')
CEN_API = os.environ.get('BENCH_CEN_API', 'http://localhost:8001')
HUB_API = os.environ.get('BENCH_HUB_API', 'http://localhost:8002')

#: Le hub vu depuis un conteneur d'instance. Chaque projet Compose a son propre
#: réseau : le nom de service `hub` n'y est pas résolvable, seul le port publié
#: sur l'hôte l'est.
HUB_DEPUIS_CONTENEUR = os.environ.get(
    'BENCH_HUB_INTERNE', 'http://host.docker.internal:8002'
)

RNF_WEB = 'cicada_web'
CEN_WEB = 'cicada_cen_web'
HUB_CONTENEUR = 'cicada_hub_api'

IDENTIFIANTS = {'username': 'admin@test.fr', 'password': 'Test123!'}
DELAI = 60

MARQUEUR = '###BENCH###'

if sys.stdout.isatty():
    VERT, ROUGE, JAUNE, GRAS, RAZ = (
        '\033[32m', '\033[31m', '\033[33m', '\033[1m', '\033[0m'
    )
else:
    VERT = ROUGE = JAUNE = GRAS = RAZ = ''


class EchecDuBanc(AssertionError):
    """Un invariant du banc n'est pas tenu."""


# --------------------------------------------------------------------------- #
# Pilotage des briques
# --------------------------------------------------------------------------- #

class Banc:
    """Accès aux trois briques : HTTP pour les API, docker pour les commandes."""

    def __init__(self):
        self.jeton_lecture = self._lire_env('.env.hub', 'HUB_READ_TOKEN')
        self._jetons_depot = self._jetons_de_depot()
        self._jetons_jwt = {}

    @staticmethod
    def _jetons_de_depot():
        """
        Jetons de dépôt, lus dans `.env.hub` — la source de vérité du hub.

        Le banc ne suppose **pas** les instances configurées pour publier : il
        passe l'adresse et le jeton à chaque appel. Sans ça, les tests
        échoueraient sur un `.env` incomplet plutôt que sur un vrai défaut, et
        la première question serait « le test est-il cassé ? ».
        """
        brut = Banc._lire_env('.env.hub', 'HUB_FEDERATION_TOKENS')
        jetons = {}
        for paire in brut.split(','):
            instance, _, jeton = paire.partition(':')
            if instance.strip() and jeton.strip():
                jetons[instance.strip()] = jeton.strip()
        if not jetons:
            raise EchecDuBanc("HUB_FEDERATION_TOKENS vide dans .env.hub")
        return jetons

    # -- configuration ----------------------------------------------------- #

    @staticmethod
    def _lire_env(fichier, cle):
        chemin = os.path.join(RACINE, fichier)
        try:
            with open(chemin, encoding='utf-8') as fh:
                for ligne in fh:
                    if ligne.startswith(f'{cle}='):
                        return ligne.split('=', 1)[1].strip()
        except FileNotFoundError:
            pass
        raise EchecDuBanc(f"{cle} introuvable dans {fichier}")

    # -- HTTP -------------------------------------------------------------- #

    def hub(self, chemin, **params):
        """Interroge l'API de lecture du hub."""
        reponse = requests.get(
            f'{HUB_API}{chemin}', params=params,
            headers={'X-Hub-Token': self.jeton_lecture}, timeout=DELAI,
        )
        return reponse

    def jwt(self, api):
        """Jeton d'une instance, obtenu une fois puis mémorisé."""
        if api not in self._jetons_jwt:
            reponse = requests.post(
                f'{api}/api/auth/login/', json=IDENTIFIANTS, timeout=DELAI,
            )
            if reponse.status_code != 200:
                raise EchecDuBanc(
                    f"Connexion refusée sur {api} : {reponse.status_code} "
                    f"{reponse.text[:200]}"
                )
            self._jetons_jwt[api] = reponse.json()['access']
        return self._jetons_jwt[api]

    def instance(self, api, chemin, **params):
        """Interroge l'API d'une instance CICADA, authentifié."""
        return requests.get(
            f'{api}{chemin}', params=params,
            headers={'Authorization': f'Bearer {self.jwt(api)}'}, timeout=DELAI,
        )

    # -- docker ------------------------------------------------------------ #

    @staticmethod
    def docker(conteneur, *commande, env=None, entree=None, attendre_succes=True):
        """Exécute une commande dans un conteneur et rend (code, sortie)."""
        prefixe = ['docker', 'exec']
        for cle, valeur in (env or {}).items():
            prefixe += ['-e', f'{cle}={valeur}']
        if entree is not None:
            prefixe.append('-i')
        resultat = subprocess.run(
            [*prefixe, conteneur, *commande],
            input=entree, capture_output=True, text=True, timeout=900,
        )
        sortie = resultat.stdout + resultat.stderr
        if attendre_succes and resultat.returncode != 0:
            raise EchecDuBanc(
                f"« {' '.join(commande)} » a échoué dans {conteneur} :\n"
                f"{sortie[-1500:]}"
            )
        return resultat.returncode, sortie

    def django(self, conteneur, code, env=None):
        """
        Exécute du code Django et rend ce qu'il a imprimé après le marqueur.

        Le marqueur est nécessaire : le shell Django écrit des lignes de
        journalisation avant et après, qu'on ne peut pas distinguer autrement de
        la sortie utile.
        """
        script = f"{code}\n"
        _, sortie = self.docker(
            conteneur, 'python', 'manage.py', 'shell', env=env, entree=script,
        )
        lignes = [ligne for ligne in sortie.splitlines() if ligne.startswith(MARQUEUR)]
        return [ligne[len(MARQUEUR):].strip() for ligne in lignes]

    # -- actions ----------------------------------------------------------- #

    def publier(self, conteneur, *arguments, env=None, attendre_succes=True):
        """
        Déclenche une publication, en fournissant hub et jeton explicitement.

        L'adresse est celle vue **depuis un conteneur d'instance** : chaque
        projet Compose a son propre réseau, le hub n'est joignable que par son
        port publié sur l'hôte.
        """
        instance_id = 'cen' if conteneur == CEN_WEB else 'rnf'
        return self.docker(
            conteneur, 'python', 'manage.py', 'push_federation',
            '--hub', HUB_DEPUIS_CONTENEUR,
            '--token', self._jetons_depot[instance_id],
            *arguments,
            env=env, attendre_succes=attendre_succes,
        )

    def reindexer(self, conteneur):
        return self.docker(
            conteneur, 'python', 'manage.py', 'rebuild_search_index', '--purge',
        )

    def etat_du_hub(self, instance_id):
        """(nombre de plans, nombre de documents) publiés par une instance."""
        plans = self.hub('/api/exploration/plans/', instances=instance_id, page_size=1)
        contenus = self.hub(
            '/api/exploration/contenus/', instances=instance_id, page_size=1
        )
        for reponse in (plans, contenus):
            if reponse.status_code != 200:
                raise EchecDuBanc(
                    f"Hub : {reponse.status_code} {reponse.text[:200]}"
                )
        return (
            plans.json()['pagination']['count'],
            contenus.json()['pagination']['count'],
        )

    def statut_du_plan(self, conteneur, slug, statut=None):
        """Lit, ou change puis réindexe, le statut d'un plan."""
        if statut is None:
            lignes = self.django(conteneur, f"""
from apps.plans.models import PlanGestion
print('{MARQUEUR}' + PlanGestion.objects.get(slug={slug!r}).statut)
""")
            return lignes[0]

        self.django(conteneur, f"""
from apps.plans.models import PlanGestion
from apps.search.indexing import index_plan, desindexer_plan
plan = PlanGestion.objects.get(slug={slug!r})
plan.statut = {statut!r}
plan.save(update_fields=['statut'])
(index_plan if {statut!r} in PlanGestion.VALIDATED_STATUSES else desindexer_plan)(plan)
print('{MARQUEUR}ok')
""")
        return statut


RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --------------------------------------------------------------------------- #
# Contrat — ce que CICADA produit, le hub doit savoir le lire
# --------------------------------------------------------------------------- #

def cas_contrat_la_charge_utile_passe_la_validation_du_hub(banc):
    """
    Le producteur et le consommateur se parlent, pour de vrai.

    Chaque projet avait ses tests, écrits contre sa propre lecture du contrat.
    C'est exactement là que les bugs se logent : un champ renommé d'un côté
    passe les 195 tests et casse la publication en production.

    On prend une charge utile réellement construite par CICADA et on la fait
    valider par le sérialiseur du hub — sans rien écrire.
    """
    lignes = banc.django(RNF_WEB, f"""
import json
from apps.search.push import charge_utile, plans_a_publier
from apps.search.serializers import prefetch_sites
plan = plans_a_publier().prefetch_related(prefetch_sites()).first()
print('{MARQUEUR}' + json.dumps(charge_utile(plan), default=str))
""")
    if not lignes:
        raise EchecDuBanc("Aucune charge utile produite : RNF a-t-il des plans ?")
    charge = lignes[0]

    _, sortie = banc.docker(HUB_CONTENEUR, 'python', '-c', f"""
import json, sys, django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.index.serializers_federation import PlanPublieSerializer
donnees = json.loads(sys.stdin.read())
serialiseur = PlanPublieSerializer(data=donnees)
if serialiseur.is_valid():
    print('{MARQUEUR}VALIDE ' + str(len(donnees.get('contenus') or [])))
else:
    print('{MARQUEUR}INVALIDE ' + json.dumps(serialiseur.errors))
""", entree=charge)

    verdict = next(
        (l[len(MARQUEUR):].strip() for l in sortie.splitlines()
         if l.startswith(MARQUEUR)), '',
    )
    if not verdict.startswith('VALIDE'):
        raise EchecDuBanc(f"Le hub refuse la charge utile de CICADA : {verdict}")
    return f"charge utile acceptée ({verdict.split()[1]} documents)"


def cas_contrat_la_fiche_voyage_en_json_pur(banc):
    """
    La fiche est un instantané publié, pas un modèle répliqué.

    `FichePubliqueSerializer` évolue avec `apps.plans`. Le jour où sa sortie
    contient un objet non sérialisable — une date, un Decimal — la publication
    échoue à l'envoi, loin de la cause.
    """
    lignes = banc.django(RNF_WEB, f"""
import json
from apps.search.push import charge_utile, plans_a_publier
from apps.search.serializers import prefetch_sites
plan = plans_a_publier().prefetch_related(prefetch_sites()).first()
fiche = charge_utile(plan)['fiche']
json.dumps(fiche)                       # lève si un type ne passe pas
print('{MARQUEUR}' + str(len(fiche.get('enjeux') or [])))
""")
    return f"fiche sérialisable ({lignes[0]} enjeux)"


# --------------------------------------------------------------------------- #
# Scénarios de banc
# --------------------------------------------------------------------------- #

def cas_aller_retour_le_contenu_publie_devient_cherchable(banc):
    """Publier depuis CICADA, puis retrouver le contenu par le hub."""
    banc.publier(RNF_WEB)
    plans, documents = banc.etat_du_hub('rnf')
    if plans == 0 or documents == 0:
        raise EchecDuBanc(
            f"Rien de publié pour rnf ({plans} plans, {documents} documents)"
        )
    return f"{plans} plans, {documents} documents cherchables"


def cas_isolation_une_instance_ne_purge_pas_l_autre(banc):
    """
    L'invariant le plus important du système.

    La purge à la bascule est bornée à l'instance du lot. Sans cette borne, un
    jeton compromis suffirait à vider l'index d'un autre organisme en basculant
    un lot vide.
    """
    avant = banc.etat_du_hub('rnf')
    banc.publier(CEN_WEB)
    apres = banc.etat_du_hub('rnf')
    if avant != apres:
        raise EchecDuBanc(
            f"Publier depuis le CEN a modifié l'index de RNF : {avant} → {apres}"
        )
    return f"RNF intact ({apres[0]} plans) après publication du CEN"


def cas_depublication_un_plan_retire_disparait(banc):
    """
    L'état fait foi : aucun message de retrait ne circule.

    Un index alimenté par événements finirait par laisser visible un plan que
    son gestionnaire a dépublié — un incident, pas une gêne.
    """
    lignes = banc.django(RNF_WEB, f"""
from apps.plans.models import PlanGestion
plan = PlanGestion.objects.filter(statut='valide').order_by('pk').first()
print('{MARQUEUR}' + plan.slug)
""")
    slug = lignes[0]
    plans_avant, _ = banc.etat_du_hub('rnf')

    try:
        banc.statut_du_plan(RNF_WEB, slug, 'draft')
        banc.publier(RNF_WEB)

        plans_apres, _ = banc.etat_du_hub('rnf')
        if plans_apres != plans_avant - 1:
            raise EchecDuBanc(
                f"Le plan dépublié n'a pas disparu : {plans_avant} → {plans_apres}"
            )

        fiche = banc.hub(f'/api/exploration/plans/rnf:{slug}/')
        if fiche.status_code != 404:
            raise EchecDuBanc(
                f"La fiche du plan dépublié répond encore ({fiche.status_code})"
            )
    finally:
        # Restauration systématique : le banc doit ressortir comme il est entré.
        banc.statut_du_plan(RNF_WEB, slug, 'valide')
        banc.publier(RNF_WEB)

    retabli, _ = banc.etat_du_hub('rnf')
    if retabli != plans_avant:
        raise EchecDuBanc(
            f"État non rétabli : {plans_avant} plans avant, {retabli} après"
        )
    return f"« {slug} » retiré puis rétabli, fiche en 404 entre-temps"


def cas_idempotence_republier_ne_change_rien(banc):
    """
    Publier deux fois d'affilée doit laisser exactement le même état.

    C'est ce qui rend une publication périodique sans danger : si le second
    passage retirait ou dupliquait quoi que ce soit, une tâche planifiée
    dégraderait l'index à chaque exécution.
    """
    banc.publier(RNF_WEB)
    premier = banc.etat_du_hub('rnf')
    banc.publier(RNF_WEB)
    second = banc.etat_du_hub('rnf')
    if premier != second:
        raise EchecDuBanc(f"Republication non idempotente : {premier} → {second}")
    return f"état stable ({premier[0]} plans, {premier[1]} documents)"


def cas_garde_fou_une_identite_inconnue_refuse_de_publier(banc):
    """
    Le garde-fou qui rend visible l'échec le plus sournois.

    La charge utile ne retient que les lignes d'index portant l'identité de
    l'instance. Si l'index a été construit sous une autre, la publication
    « réussit » en déposant des plans **sans aucun document** : l'exploration
    les affiche en mode plan, mais aucune recherche de contenu ne les trouve.
    """
    code, sortie = banc.publier(
        RNF_WEB, env={'CICADA_INSTANCE_ID': 'identite-inexistante'},
        attendre_succes=False,
    )
    if code == 0:
        raise EchecDuBanc(
            "La publication a réussi sous une identité sans index — elle aurait "
            "déposé des plans vides de tout document."
        )
    if 'rebuild_search_index' not in sortie:
        raise EchecDuBanc(
            f"Échec attendu, mais sans indiquer la marche à suivre :\n{sortie[-400:]}"
        )
    return "publication refusée, avec la commande de réparation"


def cas_securite_le_hub_refuse_un_jeton_de_lecture_invalide(banc):
    """Le hub n'est pas public : il agrège le contenu de plusieurs organismes."""
    reponse = requests.get(
        f'{HUB_API}/api/exploration/contenus/',
        headers={'X-Hub-Token': 'jeton-invente'}, timeout=DELAI,
    )
    if reponse.status_code != 403:
        raise EchecDuBanc(
            f"Jeton invalide accepté ou mal rejeté : {reponse.status_code}"
        )
    return "403 sur jeton invalide"


# --------------------------------------------------------------------------- #
# Parité — le test le plus important
# --------------------------------------------------------------------------- #

#: Requêtes couvrant les facettes, les deux modes de recherche et les tris.
#: Chacune doit rendre le même résultat servie localement ou par le hub.
REQUETES_DE_PARITE = [
    {},
    {'q': 'foret'},
    {'q': 'foret', 'titres_seulement': 'false'},
    {'q': 'zones humides'},
    {'types': 'enjeu'},
    {'types': 'action,pression'},
    {'statuts': 'valide'},
    {'statuts': 'archive'},
    {'statuts': 'en_cours'},
    {'types_site': 'RNN'},
    {'categories_enjeu': 'ecologique'},
    {'types_indicateur': 'ETAT'},
    {'tri': 'alphabetique'},
    {'tri': 'recent'},
]


def _cles(resultats):
    """Identité d'un document, comparable entre les deux implémentations."""
    return {(r['type_contenu'], r['id_objet']) for r in resultats}


def cas_parite_local_et_hub_repondent_pareil(banc):
    """
    La même recherche, sur le même corpus, doit rendre le même résultat.

    `filters.py` existe en deux exemplaires, un par projet. Sans ce test, les
    deux implémentations divergeraient en silence — et une divergence de
    filtrage se constate sans pouvoir se décrire : « il manque des résultats ».

    Le corpus est celui de RNF, présent des deux côtés : localement dans son
    index, et sur le hub sous `instances=rnf`.
    """
    banc.publier(RNF_WEB)
    ecarts = []

    for parametres in REQUETES_DE_PARITE:
        local = banc.instance(
            RNF_API, '/api/exploration/contenus/', page_size=100, **parametres
        )
        distant = banc.hub(
            '/api/exploration/contenus/', page_size=100,
            instances='rnf', **parametres,
        )
        if local.status_code != 200 or distant.status_code != 200:
            ecarts.append(
                f"{parametres} → HTTP local {local.status_code} / "
                f"hub {distant.status_code}"
            )
            continue

        local, distant = local.json(), distant.json()
        n_local = local['pagination']['count']
        n_distant = distant['pagination']['count']
        if n_local != n_distant:
            ecarts.append(f"{parametres} → {n_local} en local, {n_distant} au hub")
            continue

        manquants = _cles(local['results']) - _cles(distant['results'])
        surnumeraires = _cles(distant['results']) - _cles(local['results'])
        if manquants or surnumeraires:
            ecarts.append(
                f"{parametres} → {len(manquants)} absents du hub, "
                f"{len(surnumeraires)} en trop"
            )

    if ecarts:
        raise EchecDuBanc(
            "Les deux implémentations de filtrage divergent :\n    "
            + "\n    ".join(ecarts)
        )
    return f"{len(REQUETES_DE_PARITE)} requêtes identiques des deux côtés"


def cas_parite_les_compteurs_d_onglets_concordent(banc):
    """
    Les compteurs alimentent les onglets « Tout (24) / Pressions (2) ».

    Ils sont calculés avant le filtre d'onglet des deux côtés — un écart ici
    signale que l'une des implémentations l'applique trop tôt.
    """
    local = banc.instance(RNF_API, '/api/exploration/contenus/', page_size=1).json()
    distant = banc.hub(
        '/api/exploration/contenus/', instances='rnf', page_size=1
    ).json()

    ecarts = {
        cle: (local['compteurs'].get(cle), distant['compteurs'].get(cle))
        for cle in set(local['compteurs']) | set(distant['compteurs'])
        if local['compteurs'].get(cle) != distant['compteurs'].get(cle)
    }
    if ecarts:
        raise EchecDuBanc(f"Compteurs discordants (local, hub) : {ecarts}")
    return f"compteurs identiques ({local['compteurs']['tout']} documents)"


def cas_parite_la_fiche_distante_vaut_la_locale(banc):
    """
    La fiche publiée doit dire la même chose que celle assemblée en direct.

    C'est ce qui rend l'instantané défendable : il vieillit, mais il ne ment
    pas au moment où il est pris.
    """
    lignes = banc.django(RNF_WEB, f"""
from apps.plans.models import PlanGestion
plan = (PlanGestion.objects.filter(statut='valide')
        .order_by('pk').first())
print('{MARQUEUR}' + plan.slug)
""")
    slug = lignes[0]
    banc.publier(RNF_WEB)

    locale = banc.instance(RNF_API, f'/api/exploration/plans/{slug}/')
    distante = banc.hub(f'/api/exploration/plans/rnf:{slug}/')
    if locale.status_code != 200 or distante.status_code != 200:
        raise EchecDuBanc(
            f"Fiche indisponible : local {locale.status_code}, "
            f"hub {distante.status_code}"
        )

    # Comparaison **à plat des deux côtés**. Déballer un `['fiche']` ici
    # masquerait exactement ce qu'il faut vérifier : que le hub sert la fiche
    # dans la même forme qu'une instance. C'est ce que faisait la première
    # version de ce test, et l'incompatibilité n'est ressortie qu'en E2E, sur
    # une page au titre vide.
    locale, distante = locale.json(), distante.json()
    divergences = [
        champ for champ in ('id_pg', 'nom', 'slug', 'annee_debut', 'annee_fin')
        if locale.get(champ) != distante.get(champ)
    ]
    if len(locale.get('enjeux') or []) != len(distante.get('enjeux') or []):
        divergences.append('enjeux')
    if divergences:
        raise EchecDuBanc(f"La fiche publiée diverge de la locale : {divergences}")
    return f"fiche « {slug} » conforme ({len(distante.get('enjeux') or [])} enjeux)"


# --------------------------------------------------------------------------- #
# Exécution
# --------------------------------------------------------------------------- #

GROUPES = [
    ("Contrat entre les deux projets", [
        cas_contrat_la_charge_utile_passe_la_validation_du_hub,
        cas_contrat_la_fiche_voyage_en_json_pur,
    ]),
    ("Scénarios de fédération", [
        cas_aller_retour_le_contenu_publie_devient_cherchable,
        cas_isolation_une_instance_ne_purge_pas_l_autre,
        cas_depublication_un_plan_retire_disparait,
        cas_idempotence_republier_ne_change_rien,
        cas_garde_fou_une_identite_inconnue_refuse_de_publier,
        cas_securite_le_hub_refuse_un_jeton_de_lecture_invalide,
    ]),
    ("Parité entre l'index local et le hub", [
        cas_parite_local_et_hub_repondent_pareil,
        cas_parite_les_compteurs_d_onglets_concordent,
        cas_parite_la_fiche_distante_vaut_la_locale,
    ]),
]


def verifier_le_banc():
    """Refuse de commencer si une brique manque — plutôt que d'échouer partout."""
    manquants = []
    for nom, url in (
        ('RNF', f'{RNF_API}/api/auth/health/'),
        ('CEN', f'{CEN_API}/api/auth/health/'),
        ('hub', f'{HUB_API}/api/health/'),
    ):
        try:
            if requests.get(url, timeout=5).status_code != 200:
                manquants.append(nom)
        except requests.RequestException:
            manquants.append(nom)
    if manquants:
        print(
            f"{ROUGE}Briques injoignables : {', '.join(manquants)}{RAZ}\n"
            f"Lancer « scripts/federation.sh up » d'abord."
        )
        sys.exit(2)


def main():
    verifier_le_banc()
    banc = Banc()
    reussis = echecs = 0

    for titre, cas in GROUPES:
        print(f"\n{GRAS}{titre}{RAZ}")
        for fonction in cas:
            nom = fonction.__name__.removeprefix('cas_').replace('_', ' ')
            try:
                detail = fonction(banc)
            except EchecDuBanc as echec:
                echecs += 1
                print(f"  {ROUGE}✗{RAZ} {nom}")
                for ligne in str(echec).splitlines():
                    print(f"      {ROUGE}{ligne}{RAZ}")
            except Exception:  # noqa: BLE001 — un imprévu ne doit pas tout arrêter
                echecs += 1
                print(f"  {ROUGE}✗{RAZ} {nom}  {JAUNE}(erreur inattendue){RAZ}")
                for ligne in traceback.format_exc().strip().splitlines()[-4:]:
                    print(f"      {JAUNE}{ligne}{RAZ}")
            else:
                reussis += 1
                print(f"  {VERT}✓{RAZ} {nom}" + (f"  — {detail}" if detail else ''))

    total = reussis + echecs
    couleur = VERT if not echecs else ROUGE
    print(f"\n{couleur}{reussis}/{total} cas passés{RAZ}\n")
    return 1 if echecs else 0


if __name__ == '__main__':
    sys.exit(main())
