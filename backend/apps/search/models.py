"""
Index de recherche du contenu des plans de gestion.

Une ligne par objet explorable (enjeu, facteur d'influence, pression, objectif
à long terme, objectif opérationnel, indicateur, action), dénormalisée pour que
l'exploration des données réponde en une seule requête, filtres et compteurs
d'onglets compris.

**Un seul index pour tous les types** : l'onglet « Tout » et le tri par
pertinence transverse imposent de classer pressions, actions et enjeux dans une
même liste, ce que des index séparés aux scores non comparables ne permettent
pas.

**Périmètre** : seuls les plans validés, modifiés ou archivés sont indexés — un
brouillon n'est pas explorable. L'indexation est donc un traitement par lot
déclenché au changement de statut (cf. ``apps/search/signals.py``), et non une
synchronisation champ par champ : le contenu d'un plan validé est verrouillé en
lecture seule (#248) et ne bouge plus.

Les deux vecteurs de recherche sont des **colonnes générées** par PostgreSQL :
elles ne peuvent pas diverger du texte indexé, et aucune étape Python ne peut
être oubliée.

- ``search_titre`` : libellés (poids A) **et objets rattachés** (poids B) —
  mode « rechercher dans les titres uniquement », activé par défaut. Depuis
  #634, chercher une espèce, un habitat, un protocole standardisé, un élément
  géologique ou une référence PressRef doit remonter les objets qui les portent
  sans avoir à élargir la recherche : ce sont des rattachements explicites, pas
  du texte de contexte.
- ``search_description``, ``search_contexte`` (libellés des ancêtres) et
  ``search_enfants`` (libellés des descendants) : un vecteur par **axe de
  portée** (#681). L'utilisateur coche « aussi dans les descriptions », « dans
  les éléments parents », « dans les éléments enfants » indépendamment ;
- ``search_full`` : la réunion de tous — c'est lui qui porte l'index GIN
  servant toute portée élargie, les axes étant ensuite revérifiés exactement.

La frontière de base n'est donc pas « titre / reste » mais « ce que l'objet
**est et porte** » d'un côté, « ce que ses parents ou ses enfants disent » de
l'autre. Le chemin d'ascendance (``chemin``) permet d'afficher l'arborescence
qui mène à l'objet retrouvé et de surligner le maillon qui a répondu (#682).
"""

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models
from django.utils.translation import gettext_lazy as _

#: Configuration de recherche plein texte : radicalisation française + suppression
#: des accents (créée par la migration initiale de l'app).
SEARCH_CONFIG = 'public.french_unaccent'


class ContenuIndexe(models.Model):
    """Un objet du contenu d'un plan de gestion, prêt à être recherché."""

    TYPE_ENJEU = 'enjeu'
    TYPE_FACTEUR = 'facteur'
    TYPE_PRESSION = 'pression'
    TYPE_OBJECTIF_LT = 'objectif_lt'
    TYPE_OBJECTIF_OP = 'objectif_op'
    TYPE_INDICATEUR = 'indicateur'
    TYPE_ACTION = 'action'

    TYPE_CHOICES = [
        (TYPE_ENJEU, _("Enjeu")),
        (TYPE_FACTEUR, _("Facteur d'influence")),
        (TYPE_PRESSION, _("Pression")),
        (TYPE_OBJECTIF_LT, _("Objectif à long terme")),
        (TYPE_OBJECTIF_OP, _("Objectif opérationnel")),
        (TYPE_INDICATEUR, _("Indicateur")),
        (TYPE_ACTION, _("Action")),
    ]

    id = models.BigAutoField(primary_key=True)

    # ------------------------------------------------------------------ #
    # Identité de l'objet indexé
    # ------------------------------------------------------------------ #
    instance_id = models.CharField(
        _("Instance d'origine"),
        max_length=64,
        default='local',
        db_index=True,
        help_text=_(
            "Déploiement CICADA dont provient le document (#636). Vaut "
            "`settings.CICADA_INSTANCE_ID` pour les documents produits ici, et "
            "l'identifiant de l'émetteur pour un document reçu d'une autre "
            "instance. C'est la seule chose qui rende `id_objet` non ambigu : "
            "toutes les clés primaires de l'application sont des séquences "
            "locales."
        ),
    )
    type_contenu = models.CharField(
        _("Type de contenu"), max_length=20, choices=TYPE_CHOICES
    )
    id_objet = models.IntegerField(
        _("Identifiant de l'objet"),
        help_text=_("Clé primaire dans la table métier correspondante."),
    )
    id_pg = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.CASCADE,
        db_column='id_pg',
        related_name='contenus_indexes',
        verbose_name=_("Plan de gestion"),
        null=True, blank=True,
        help_text=_(
            "NULL pour un document reçu d'une autre instance : le plan n'existe "
            "pas dans cette base. Le bandeau à afficher est alors dans "
            "`plan_denorm`."
        ),
    )
    plan_denorm = models.JSONField(
        _("Bandeau du plan (documents distants)"),
        default=dict, blank=True,
        help_text=_(
            "Snapshot du bandeau « plan / gestionnaire / période » d'une tuile, "
            "capturé au moment de la publication. Renseigné uniquement pour les "
            "documents distants : pour les documents locaux, ces libellés "
            "restent joints à la volée et ne peuvent donc pas devenir obsolètes."
        ),
    )
    index_version = models.PositiveSmallIntegerField(
        _("Version des extracteurs"),
        default=0,
        db_index=True,
        help_text=_(
            "Version d'`apps.search.indexing` qui a produit la ligne (#634). "
            "Une ligne écrite par une version antérieure est périmée : le "
            "contenu du plan n'ayant plus le droit de bouger une fois validé, "
            "rien ne la réécrirait autrement, et une recherche ajoutée depuis "
            "ne trouverait jamais rien. 0 = index antérieur au suivi de version."
        ),
    )

    # ------------------------------------------------------------------ #
    # Texte recherché
    # ------------------------------------------------------------------ #
    titre = models.CharField(_("Libellé"), max_length=500)
    description = models.TextField(_("Description"), blank=True, default='')
    rattachements = models.TextField(
        _("Objets rattachés"),
        blank=True,
        default='',
        help_text=_(
            "Espèces (noms scientifiques ET vernaculaires), habitats, éléments "
            "géologiques, protocoles standardisés, références PressRef et "
            "catégories d'action rattachés à l'objet ou à son enjeu. "
            "Interrogé dans les DEUX modes (#634)."
        ),
    )
    contexte = models.TextField(
        _("Contexte"),
        blank=True,
        default='',
        help_text=_(
            "Libellés des objets ancêtres. Interrogé seulement si la portée "
            "« éléments parents » est cochée."
        ),
    )
    enfants = models.TextField(
        _("Descendance"),
        blank=True,
        default='',
        help_text=_(
            "Libellés des objets descendants (#682) : un enjeu porte ici ses "
            "objectifs, indicateurs, métriques et actions. Interrogé seulement "
            "si la portée « éléments enfants » est cochée — c'est ce qui fait "
            "ressortir un enjeu quand c'est l'un de ses objectifs qui porte le "
            "mot cherché."
        ),
    )

    # ------------------------------------------------------------------ #
    # Affichage de la tuile de résultat
    # ------------------------------------------------------------------ #
    parent_type = models.CharField(
        _("Type du parent"), max_length=20, null=True, blank=True,
        help_text=_(
            "Code du type de l'objet parent. Volontairement libre : le parent "
            "d'une action peut être un suivi/inventaire, qui n'est pas lui-même "
            "un type explorable."
        ),
    )
    parent_libelle = models.CharField(
        _("Libellé du parent"), max_length=500, null=True, blank=True,
    )
    chemin = models.JSONField(
        _("Ascendance"),
        default=list, blank=True,
        help_text=_(
            "Ancêtres de l'objet, de l'enjeu jusqu'au parent direct, sous la "
            "forme [{type, id, libelle}] (#682). C'est ce qui permet à une tuile "
            "de résultat de montrer l'arborescence qui mène à l'objet retrouvé — "
            "et, en mode élargi, de désigner l'ancêtre dont le libellé a "
            "répondu. `parent_type` / `parent_libelle` en sont le dernier "
            "maillon, conservés pour les lecteurs qui ne connaissent pas cette "
            "colonne."
        ),
    )
    enjeu_slug = models.CharField(
        _("Slug de l'enjeu de la branche"), max_length=255, null=True, blank=True,
        help_text=_(
            "Slug de l'enjeu dont l'objet descend (le sien pour un enjeu). Sert "
            "à ouvrir l'arborescence réelle du plan sur la bonne branche (#683)."
        ),
    )
    sous_type = models.CharField(
        _("Sous-type"), max_length=50, null=True, blank=True,
        help_text=_(
            "Code de la facette propre au type : `ecologique`/`socioeco` pour "
            "un enjeu, `ETAT`/`PRESSION`/`REPONSE` pour un indicateur, code de "
            "catégorie d'action (`SP`, `CS`…) pour une action."
        ),
    )
    sous_type_libelle = models.CharField(
        _("Libellé du sous-type"), max_length=255, null=True, blank=True,
    )

    # ------------------------------------------------------------------ #
    # Facettes héritées du plan (dénormalisées pour le filtrage et les
    # compteurs : une jointure de moins par facette et par requête)
    # ------------------------------------------------------------------ #
    statut_pg = models.CharField(_("Statut du plan"), max_length=20)
    annee_debut = models.IntegerField(_("Année de début"), null=True, blank=True)
    annee_fin = models.IntegerField(_("Année de fin"), null=True, blank=True)
    # #676 — prolongation du plan (#250) : il reste « en cours » jusqu'à
    # annee_fin + annees_extension. Même nom que sur `PlanGestion`, pour que
    # `q_statuts()` s'applique indifféremment au plan et à l'index.
    annees_extension = models.PositiveSmallIntegerField(
        _("Années d'extension"), default=0,
    )
    site_ids = ArrayField(
        models.IntegerField(), verbose_name=_("Sites"), default=list, blank=True,
    )
    organisme_ids = ArrayField(
        models.IntegerField(),
        verbose_name=_("Organismes gestionnaires"),
        default=list, blank=True,
    )
    type_site_codes = ArrayField(
        models.CharField(max_length=25),
        verbose_name=_("Types d'aires protégées"),
        default=list, blank=True,
    )
    area_ids = ArrayField(
        models.IntegerField(),
        verbose_name=_("Zones géographiques"),
        default=list, blank=True,
        help_text=_("Identifiants ref_geo des départements ET des régions."),
    )

    # ------------------------------------------------------------------ #
    # Vecteurs de recherche (colonnes générées par PostgreSQL)
    # ------------------------------------------------------------------ #
    search_titre = models.GeneratedField(
        expression=(
            SearchVector('titre', weight='A', config=SEARCH_CONFIG)
            + SearchVector('rattachements', weight='B', config=SEARCH_CONFIG)
        ),
        output_field=SearchVectorField(),
        db_persist=True,
        verbose_name=_("Vecteur — libellé et objets rattachés"),
    )
    # Un vecteur par axe de portée (#681). Ils ne portent pas d'index GIN :
    # une portée intermédiaire (« aussi dans les descriptions », sans les
    # parents) est servie par l'index de `search_full`, qui en est un
    # sur-ensemble, puis revérifiée exactement sur ces colonnes — cf.
    # `filters.vecteur_de_portee`.
    search_description = models.GeneratedField(
        expression=SearchVector('description', weight='B', config=SEARCH_CONFIG),
        output_field=SearchVectorField(),
        db_persist=True,
        verbose_name=_("Vecteur — description"),
    )
    search_contexte = models.GeneratedField(
        expression=SearchVector('contexte', weight='C', config=SEARCH_CONFIG),
        output_field=SearchVectorField(),
        db_persist=True,
        verbose_name=_("Vecteur — éléments parents"),
    )
    search_enfants = models.GeneratedField(
        expression=SearchVector('enfants', weight='C', config=SEARCH_CONFIG),
        output_field=SearchVectorField(),
        db_persist=True,
        verbose_name=_("Vecteur — éléments enfants"),
    )
    search_full = models.GeneratedField(
        expression=(
            SearchVector('titre', weight='A', config=SEARCH_CONFIG)
            + SearchVector('rattachements', weight='B', config=SEARCH_CONFIG)
            + SearchVector('description', weight='B', config=SEARCH_CONFIG)
            + SearchVector('contexte', weight='C', config=SEARCH_CONFIG)
            + SearchVector('enfants', weight='C', config=SEARCH_CONFIG)
        ),
        output_field=SearchVectorField(),
        db_persist=True,
        verbose_name=_("Vecteur — texte complet"),
    )

    date_indexation = models.DateTimeField(_("Indexé le"), auto_now=True)

    class Meta:
        db_table = '"ccd_search"."t_recherche_contenu"'
        verbose_name = _("Contenu indexé")
        verbose_name_plural = _("Contenus indexés")
        constraints = [
            # L'instance fait partie de la clé : deux déploiements peuvent
            # légitimement avoir un enjeu n° 42 (#636).
            models.UniqueConstraint(
                fields=['instance_id', 'type_contenu', 'id_objet'],
                name='uq_recherche_contenu_objet',
            ),
        ]
        indexes = [
            GinIndex(fields=['search_titre'], name='idx_recherche_titre_gin'),
            GinIndex(fields=['search_full'], name='idx_recherche_full_gin'),
            # Tolérance aux fautes de frappe sur les libellés…
            GinIndex(
                fields=['titre'], name='idx_recherche_titre_trgm',
                opclasses=['gin_trgm_ops'],
            ),
            # …et sur les objets rattachés (#634) : un nom d'habitat, d'espèce
            # ou de protocole est long, latin et rarement tapé sans faute — la
            # radicalisation ne pardonne rien, seule la similarité rattrape.
            GinIndex(
                fields=['rattachements'], name='idx_recherche_ratt_trgm',
                opclasses=['gin_trgm_ops'],
            ),
            GinIndex(fields=['site_ids'], name='idx_recherche_sites'),
            GinIndex(fields=['organisme_ids'], name='idx_recherche_organismes'),
            GinIndex(fields=['type_site_codes'], name='idx_recherche_types_site'),
            GinIndex(fields=['area_ids'], name='idx_recherche_areas'),
            models.Index(fields=['type_contenu'], name='idx_recherche_type'),
            models.Index(fields=['statut_pg'], name='idx_recherche_statut'),
        ]

    def __str__(self):
        return f"[{self.type_contenu}] {self.titre}"
