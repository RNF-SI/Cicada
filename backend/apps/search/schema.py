"""
Description OpenAPI (drf-spectacular) de l'exploration et de la fédération.

Les vues de ce module ne sont pas des `GenericAPIView` : elles assemblent leurs
réponses à la main (pagination enrichie de compteurs, relais vers le hub,
instantanés JSON). drf-spectacular ne peut donc rien deviner, et c'est ici que
le contrat réel est décrit — paramètres de requête lus par `filters.py`, formes
de réponse construites par `pagination.py`, `federation.py`, `raccordement.py`.

Ce module ne contient **que** de la documentation : rien ici n'est exécuté
par une requête. Si un paramètre ou un champ change dans le code, c'est ici
qu'il faut le refléter, sinon le schéma ment.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter, OpenApiResponse, inline_serializer,
)
from rest_framework import serializers

from .filters import (
    PORTEES, STATUT_ARCHIVE, STATUT_EN_COURS, STATUT_VALIDE, TRI_ALPHABETIQUE,
    TRI_PERTINENCE, TRI_RECENT,
)
from .models import ContenuIndexe
from .serializers import (
    ContenuResultatSerializer, PlanResultatSerializer, SiteResumeSerializer,
)

TAG_EXPLORATION = 'exploration'
TAG_FEDERATION = 'federation'

TYPES_CONTENU = [code for code, _ in ContenuIndexe.TYPE_CHOICES]
STATUTS_FILTRE = [STATUT_EN_COURS, STATUT_VALIDE, STATUT_ARCHIVE]
TRIS = [TRI_PERTINENCE, TRI_ALPHABETIQUE, TRI_RECENT]


# --------------------------------------------------------------------------- #
# Paramètres de requête
# --------------------------------------------------------------------------- #

def _multi(nom, description, enum=None, type_=OpenApiTypes.STR):
    """Paramètre multi-valeurs : `?nom=a,b` ou `?nom=a&nom=b` (cf. `filters.liste`)."""
    return OpenApiParameter(
        name=nom, type=type_, location=OpenApiParameter.QUERY, many=True,
        explode=False, style='form', enum=enum,
        description=f"{description} Plusieurs valeurs : séparées par des virgules, "
                    "ou paramètre répété.",
    )


PARAM_PAGE = OpenApiParameter(
    'page', OpenApiTypes.INT, OpenApiParameter.QUERY,
    description="Numéro de page (1 par défaut).",
)
PARAM_PAGE_SIZE = OpenApiParameter(
    'page_size', OpenApiTypes.INT, OpenApiParameter.QUERY,
    description="Taille de page (20 par défaut, 100 au plus).",
)

#: Facettes de plan, communes aux deux modes de recherche.
PARAMS_FACETTES_PLAN = [
    _multi('zones', "Identifiants `id_area` (ref_geo) des départements ou régions "
                    "dont au moins un site du plan relève.", type_=OpenApiTypes.INT),
    _multi('organismes', "Identifiants d'organismes gestionnaires d'un site du plan.",
           type_=OpenApiTypes.INT),
    _multi('types_site', "Mnémoniques de type d'espace protégé (RNN, RNR, PNR, ENS…) "
                         "d'un site du plan."),
    _multi('statuts', "Statut du plan : `en_cours` (validé et dont la période, "
                      "prolongation comprise, couvre l'année courante), `valide` "
                      "(validé ou modifié), `archive`.", enum=STATUTS_FILTRE),
    _multi('instances', "Structures d'origine (`instance_id`). N'a de portée réelle "
                        "qu'en exploration nationale ; en local, une liste qui "
                        "n'inclut pas cette instance vide le résultat."),
    OpenApiParameter(
        'tri', OpenApiTypes.STR, OpenApiParameter.QUERY, enum=TRIS,
        description="Ordre des résultats. `pertinence` (défaut) retombe sur "
                    "l'ordre alphabétique sans mot-clé.",
    ),
    PARAM_PAGE, PARAM_PAGE_SIZE,
]

PARAMS_CONTENUS = [
    OpenApiParameter(
        'q', OpenApiTypes.STR, OpenApiParameter.QUERY,
        description="Mot-clé (syntaxe « websearch » PostgreSQL : guillemets, `-`, "
                    "`OR`). Toujours cherché dans le libellé de l'objet et ses "
                    "rattachements (espèces, habitats, protocoles) ; la portée "
                    "élargit aux autres champs. Sans résultat exact, repli sur des "
                    "termes approchants, signalé par `approximatif`.",
    ),
    _multi('portee', "Axes de recherche en plus de l'objet lui-même : `description` "
                     "(texte descriptif), `parents` (ascendance dans l'arborescence), "
                     "`enfants` (descendance). Vide = libellé seul.",
           enum=list(PORTEES)),
    OpenApiParameter(
        'titres_seulement', OpenApiTypes.BOOL, OpenApiParameter.QUERY,
        deprecated=True,
        description="Paramètre historique : `false` vaut `portee=description,"
                    "parents,enfants`. Préférer `portee`.",
    ),
    _multi('types', "Types de contenu retenus.", enum=TYPES_CONTENU),
    _multi('onglet', "Onglet affiché : restreint les résultats **sans** toucher aux "
                     "`compteurs`, calculés sur la recherche entière. `tout` = aucun "
                     "filtre.", enum=['tout'] + TYPES_CONTENU),
    _multi('categories_enjeu', "Sous-types d'enjeu (mnémoniques de catégorie). "
                               "Ne raffine que les enjeux, les autres types restent "
                               "visibles."),
    _multi('types_indicateur', "Sous-types d'indicateur (mnémoniques). Ne raffine "
                               "que les indicateurs."),
    _multi('categories_action', "Sous-types d'action (mnémoniques de catégorie). "
                                "Ne raffine que les actions."),
    *PARAMS_FACETTES_PLAN,
]

PARAMS_PLANS = [
    OpenApiParameter(
        'q', OpenApiTypes.STR, OpenApiParameter.QUERY,
        description="Mot-clé cherché (sans accents, sous-chaîne) dans le nom du "
                    "plan, le nom de ses sites, et le nom de leurs départements "
                    "et régions.",
    ),
    *PARAMS_FACETTES_PLAN,
]


# --------------------------------------------------------------------------- #
# Formes de réponse
# --------------------------------------------------------------------------- #

#: Instanciés une seule fois : `inline_serializer` crée une classe à chaque appel,
#: et deux classes de même nom feraient signaler un conflit de composants.
LIENS_PAGINATION = inline_serializer('ExplorationLiens', fields={
    'next': serializers.URLField(allow_null=True),
    'previous': serializers.URLField(allow_null=True),
})
META_PAGINATION = inline_serializer('ExplorationPagination', fields={
    'count': serializers.IntegerField(),
    'current_page': serializers.IntegerField(),
    'total_pages': serializers.IntegerField(),
    'page_size': serializers.IntegerField(),
    'has_next': serializers.BooleanField(),
    'has_previous': serializers.BooleanField(),
})


def _pagination_fields():
    return {'links': LIENS_PAGINATION, 'pagination': META_PAGINATION}


REPONSE_CONTENUS = inline_serializer('ExplorationContenusListe', fields={
    **_pagination_fields(),
    'results': ContenuResultatSerializer(many=True),
    'approximatif': serializers.BooleanField(
        help_text="Vrai si aucun résultat exact n'existait et que la recherche "
                  "s'est rabattue sur des termes approchants (#651)."),
    'compteurs': inline_serializer('ExplorationCompteurs', fields={
        'tout': serializers.IntegerField(),
        **{type_contenu: serializers.IntegerField() for type_contenu in TYPES_CONTENU},
    }),
})

REPONSE_PLANS = inline_serializer('ExplorationPlansListe', fields={
    **_pagination_fields(),
    'results': PlanResultatSerializer(many=True),
})

INSTANCE_EXPLORATION = inline_serializer('ExplorationInstance', many=True, fields={
    'instance_id': serializers.CharField(),
    'libelle': serializers.CharField(help_text="Nom affichable de la structure."),
    'url_publique': serializers.URLField(allow_null=True),
    'plans': serializers.IntegerField(help_text="Plans présents dans l'index."),
    'contenus': serializers.IntegerField(help_text="Objets explorables indexés."),
    'derniere_publication': serializers.DateTimeField(
        allow_null=True, help_text="Dernier dépôt sur le hub ; nul en exploration locale."),
})

REPONSE_INSTANCES = inline_serializer('ExplorationInstancesListe', fields={
    'count': serializers.IntegerField(),
    'instances': INSTANCE_EXPLORATION,
})

ERREUR_DETAIL = inline_serializer('ExplorationErreur', fields={
    'detail': serializers.CharField(),
})

REPONSE_401 = OpenApiResponse(description="Authentification requise.")
REPONSE_403 = OpenApiResponse(description="Droits insuffisants.")
REPONSE_404 = OpenApiResponse(description="Introuvable.")
REPONSE_502 = OpenApiResponse(
    response=ERREUR_DETAIL,
    description="Exploration relayée vers le hub, et hub injoignable ou en erreur. "
                "Pas de repli sur l'index local : une réponse partielle sous une "
                "interface qui promet une recherche transverse serait trompeuse.",
)

#: Bandeau d'un plan tel que capturé à la publication (`federation._bandeau_du_plan`).
BANDEAU_PLAN = inline_serializer('FederationBandeauPlan', fields={
    'id_pg': serializers.IntegerField(),
    'nom': serializers.CharField(),
    'slug': serializers.CharField(),
    'statut': serializers.CharField(),
    'annee_debut': serializers.IntegerField(allow_null=True),
    'annee_fin': serializers.IntegerField(allow_null=True),
    'type_document': serializers.CharField(allow_null=True),
    'sites': SiteResumeSerializer(many=True),
    'gestionnaire_principal': serializers.CharField(allow_null=True),
})

DOCUMENT_FEDERATION = inline_serializer('FederationDocument', many=True, fields={
    'type_contenu': serializers.ChoiceField(choices=ContenuIndexe.TYPE_CHOICES),
    'id_objet': serializers.IntegerField(
        help_text="Clé primaire **locale** à l'instance émettrice : non identifiante "
                  "entre instances."),
    'titre': serializers.CharField(),
    'description': serializers.CharField(allow_null=True),
    'contexte': serializers.CharField(allow_null=True),
    'rattachements': serializers.CharField(allow_null=True),
    'enfants': serializers.CharField(allow_null=True),
    'parent_type': serializers.CharField(allow_null=True),
    'parent_libelle': serializers.CharField(allow_null=True),
    'chemin': serializers.ListField(child=serializers.DictField()),
    'enjeu_slug': serializers.CharField(allow_null=True),
    'sous_type': serializers.CharField(allow_null=True),
    'sous_type_libelle': serializers.CharField(allow_null=True),
    'statut_pg': serializers.CharField(),
    'annee_debut': serializers.IntegerField(allow_null=True),
    'annee_fin': serializers.IntegerField(allow_null=True),
    'annees_extension': serializers.IntegerField(),
    'type_site_codes': serializers.ListField(child=serializers.CharField()),
    'area_codes': serializers.ListField(
        child=serializers.CharField(),
        help_text="Zones sous la forme `TYPE:code INSEE` (ex. `DEP:25`), re-résolues "
                  "par le lecteur dans son propre ref_geo."),
    'site_inpn_codes': serializers.ListField(
        child=serializers.CharField(), help_text="Codes INPN des sites du plan."),
    'plan': BANDEAU_PLAN,
})

REPONSE_FEDERATION_DOCUMENTS = inline_serializer('FederationDocumentsListe', fields={
    **_pagination_fields(),
    'results': DOCUMENT_FEDERATION,
    'format_version': serializers.IntegerField(),
    'instance_id': serializers.CharField(),
    'instance_label': serializers.CharField(),
})

REPONSE_403_FEDERATION = OpenApiResponse(
    description="Jeton de fédération absent ou invalide, ou aucun jeton configuré "
                "sur cette instance.",
)

PARAM_JETON_FEDERATION = OpenApiParameter(
    'X-Federation-Token', OpenApiTypes.STR, OpenApiParameter.HEADER, required=True,
    description="Jeton partagé de fédération (`CICADA_FEDERATION_TOKEN`). Tout est "
                "refusé si l'instance n'en a pas configuré.",
)


# --------------------------------------------------------------------------- #
# Raccordement au hub (super administrateur)
# --------------------------------------------------------------------------- #

ERREUR_RACCORDEMENT = inline_serializer('RaccordementErreur', fields={
    'erreur': serializers.CharField(
        help_text="Clé stable, traduite par l'interface : `identite_manquante`, "
                  "`non_raccorde`, `jetons_environnement`, `deja_acceptee`, "
                  "`contact_invalide`, `pas_de_code`, `code_invalide`, "
                  "`jeton_suivi_absent`, `suivi_indisponible`, `hub_injoignable`, "
                  "`erreur_inconnue`."),
    'detail': serializers.CharField(help_text="Message lisible."),
})

ETAT_RACCORDEMENT = inline_serializer('RaccordementEtat', fields={
    'configuration': inline_serializer('RaccordementConfiguration', fields={
        'instance_id': serializers.CharField(),
        'instance_libelle': serializers.CharField(),
        'identite_valide': serializers.BooleanField(),
        'hub_url': serializers.CharField(allow_null=True),
        'source_jetons': serializers.ChoiceField(
            choices=['environnement', 'adhesion'], allow_null=True,
            help_text="D'où viennent les jetons ; nul si l'instance n'est pas raccordée."),
        'jeton_depot_defini': serializers.BooleanField(),
        'jeton_lecture_defini': serializers.BooleanField(),
        'exploration_source': serializers.ChoiceField(choices=['local', 'hub']),
        'relais_actif': serializers.BooleanField(),
        'publication_auto': serializers.BooleanField(),
        'partage': serializers.BooleanField(
            help_text="Consentement au partage (`SiteConfiguration.federation_partage`)."),
        'suivi_disponible': serializers.BooleanField(),
    }),
    'adhesion': inline_serializer('RaccordementAdhesion', fields={
        'statut': serializers.CharField(
            help_text="`''` (aucune), `en_attente`, `code_envoye`, `acceptee`, `refusee`."),
        'demandee_le': serializers.DateTimeField(allow_null=True),
        'motif': serializers.CharField(allow_null=True),
        'code_expire_le': serializers.DateTimeField(allow_null=True),
        'contact_email': serializers.CharField(allow_null=True),
        'possible': serializers.BooleanField(),
        'erreur_suivi': serializers.CharField(allow_null=True),
    }),
    'publications': inline_serializer('RaccordementPublication', many=True, fields={
        'date': serializers.DateTimeField(),
        'origine': serializers.ChoiceField(choices=['nuit', 'manuelle', 'relance']),
        'resultat': serializers.ChoiceField(
            choices=['reussie', 'echec', 'ignoree', 'retrait']),
        'plans': serializers.IntegerField(allow_null=True),
        'documents': serializers.IntegerField(allow_null=True),
        'depublies': serializers.IntegerField(allow_null=True),
        'message': serializers.CharField(allow_null=True),
    }),
    'diagnostic': inline_serializer('RaccordementDiagnostic', fields={
        'niveau': serializers.ChoiceField(choices=['ok', 'info', 'attention', 'erreur']),
        'cle': serializers.CharField(
            help_text="Cas qui s'applique, du plus bloquant au plus anodin "
                      "(`identite_manquante`, `adhesion_en_attente`, `non_raccorde`, "
                      "`partage_inactif`, `derniere_publication_echec`, `ok`…)."),
        'parametres': serializers.DictField(),
    }),
})

VERIFICATION_HUB = inline_serializer('RaccordementVerification', fields={
    'hub_joignable': serializers.BooleanField(),
    'instance_reconnue': serializers.BooleanField(allow_null=True),
    'active': serializers.BooleanField(allow_null=True),
    'derniere_publication': serializers.DateTimeField(allow_null=True),
    'plans': serializers.IntegerField(allow_null=True),
    'contenus': serializers.IntegerField(allow_null=True),
    'erreur': serializers.CharField(allow_null=True),
})

REQUETE_ADHESION = inline_serializer('RaccordementAdhesionRequete', fields={
    'contact_nom': serializers.CharField(),
    'contact_email': serializers.EmailField(),
    'contact_telephone': serializers.CharField(required=False, allow_blank=True),
    'message': serializers.CharField(required=False, allow_blank=True),
})

REQUETE_CONFIRMATION = inline_serializer('RaccordementConfirmationRequete', fields={
    'code': serializers.CharField(
        help_text="Code de confirmation reçu par e-mail. Ni stocké, ni journalisé."),
})

REQUETE_CONTACT = inline_serializer('RaccordementContactRequete', fields={
    'sujet': serializers.CharField(max_length=200),
    'message': serializers.CharField(max_length=5000),
})

#: #695 — saisie du raccordement depuis l'interface ; tout est facultatif.
REQUETE_CONFIGURATION = inline_serializer('RaccordementConfigurationRequete', fields={
    'hub_url': serializers.URLField(required=False, allow_blank=True),
    'jeton_depot': serializers.CharField(required=False, allow_blank=True, write_only=True),
    'jeton_lecture': serializers.CharField(required=False, allow_blank=True, write_only=True),
    'effacer_jetons': serializers.BooleanField(required=False),
    'exploration_source': serializers.ChoiceField(choices=['local', 'hub'], required=False),
})

REPONSE_CONTACT = inline_serializer('RaccordementContactReponse', fields={
    'statut': serializers.CharField(help_text="Toujours `envoye`."),
})

REPONSES_RACCORDEMENT_ERREURS = {
    400: OpenApiResponse(ERREUR_RACCORDEMENT, description="Requête invalide."),
    401: REPONSE_401,
    403: OpenApiResponse(description="Réservé au super administrateur."),
    409: OpenApiResponse(ERREUR_RACCORDEMENT, description="État incompatible (adhésion "
                         "déjà acceptée, jetons fournis par l'environnement…)."),
    429: OpenApiResponse(ERREUR_RACCORDEMENT, description="Trop de tentatives."),
    500: OpenApiResponse(ERREUR_RACCORDEMENT, description="Erreur inattendue."),
    502: OpenApiResponse(ERREUR_RACCORDEMENT,
                         description="Suivi RNF (ou hub) injoignable ou en erreur."),
}
