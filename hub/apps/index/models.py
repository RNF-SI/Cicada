"""
Index d'exploration agrégé (#636).

Deux tables, et deux seulement :

- :class:`PlanIndexe` — une ligne par **plan publié**, portant son bandeau
  d'affichage, ses facettes, et sa **fiche rendue** ;
- :class:`ContenuIndexe` — une ligne par **objet explorable** (enjeu, facteur,
  pression, objectif, indicateur, action), rattachée à son plan.

Le hub ne connaît aucun modèle métier de CICADA. Il ne sait pas ce qu'est un
enjeu : il sait qu'un document de type ``enjeu`` porte un libellé, une
description et des facettes.

## Pourquoi le plan est une table et non une colonne

L'index de CICADA transporte le bandeau du plan dans une colonne JSON de chaque
ligne de contenu (``plan_denorm``), parce qu'il n'a qu'une poignée de documents
distants. Le hub vise l'inverse : ~1,3 M de documents une fois les ~4 400 plans
repris, tous distants. Recopier le nom du plan, ses sites et son gestionnaire
sur chaque ligne coûterait plusieurs centaines de méga-octets pour une
information qui ne varie que par plan — et rendrait la mise à jour d'un libellé
proportionnelle au nombre d'objets du plan plutôt qu'au nombre de plans.

## Pourquoi la fiche est un instantané JSON

Servir la fiche complète d'un plan distant sans recopier ici la moitié
d'``apps.plans`` : les sérialiseurs de fiche de CICADA produisent déjà un arbre
JSON autonome, l'instance l'envoie tel quel et le hub le ressert. Le hub n'a
donc pas de modèle d'enjeu, d'objectif ni d'action à maintenir en parallèle de
celui de CICADA.

Contrepartie assumée : la fiche vieillit jusqu'à la publication suivante. C'est
acceptable parce que le contenu d'un plan validé est verrouillé en lecture seule
côté CICADA (#248) — ce qui bouge, ce sont les libellés joints (nom d'un site,
d'un organisme), pas la structure.

## Ce qui identifie une ligne

``instance_id`` entre dans **toutes** les clés d'unicité. Toutes les clés
primaires de CICADA sont des séquences locales : le plan n° 42 de RNF n'a aucun
rapport avec le plan n° 42 du CEN, et les deux instances peuvent parfaitement
avoir un enjeu n° 7.
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models
from django.utils.translation import gettext_lazy as _

#: Configuration de recherche plein texte : radicalisation française +
#: suppression des accents. Identique à celle de CICADA — les deux index doivent
#: répondre pareil au même mot pendant toute la transition.
SEARCH_CONFIG = 'public.french_unaccent'


class LotPublication(models.Model):
    """
    Un dépôt en cours, ou achevé, d'une instance.

    L'état fait foi : chaque publication envoie l'**intégralité** de ce que
    l'instance rend explorable, et le hub retire ensuite ce qui n'a pas été
    revu. C'est ce qui rend la dépublication fiable — un plan repassé en
    brouillon, supprimé, ou une instance décommissionnée disparaissent sans
    qu'aucun message de retrait n'ait eu à être reçu ni à survivre au réseau.

    Mais purger « ce qui n'a pas été revu » ne peut se faire qu'une fois **tout**
    reçu : une coupure au milieu d'un envoi viderait sinon le hub de tout ce qui
    n'était pas encore arrivé. D'où le lot, en trois temps — ouverture, pages,
    bascule. Un lot jamais basculé ne détruit rien ; il expire.

    Le lot est aussi ce qui borne les dégâts d'un jeton compromis : il porte
    l'instance qui l'a ouvert, et une instance ne peut alimenter ni basculer le
    lot d'une autre.
    """

    ETAT_OUVERT = 'ouvert'
    ETAT_BASCULE = 'bascule'
    ETAT_CHOICES = [
        (ETAT_OUVERT, _("Ouvert")),
        (ETAT_BASCULE, _("Basculé")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance_id = models.CharField(
        _("Instance émettrice"), max_length=64, db_index=True,
        help_text=_("Déduite du jeton, jamais du corps de la requête."),
    )
    etat = models.CharField(
        _("État"), max_length=10, choices=ETAT_CHOICES, default=ETAT_OUVERT,
    )
    format_version = models.PositiveSmallIntegerField(
        _("Version du format d'échange"), default=0,
    )
    date_ouverture = models.DateTimeField(_("Ouvert le"), auto_now_add=True)
    date_bascule = models.DateTimeField(_("Basculé le"), null=True, blank=True)
    plans_recus = models.IntegerField(_("Plans reçus"), default=0)
    contenus_recus = models.IntegerField(_("Contenus reçus"), default=0)
    plans_purges = models.IntegerField(
        _("Plans purgés à la bascule"), default=0,
        help_text=_("Plans de cette instance absents du lot, donc dépubliés."),
    )

    class Meta:
        db_table = '"ccd_search"."t_lot_publication"'
        verbose_name = _("Lot de publication")
        verbose_name_plural = _("Lots de publication")
        indexes = [
            models.Index(fields=['instance_id', 'etat'], name='idx_lot_instance_etat'),
        ]

    def __str__(self):
        return f"[{self.instance_id}] lot {self.id} ({self.etat})"


class PlanIndexe(models.Model):
    """Un plan de gestion publié par une instance."""

    id = models.BigAutoField(primary_key=True)
    lot = models.ForeignKey(
        LotPublication,
        on_delete=models.SET_NULL,
        db_column='id_lot',
        related_name='plans',
        verbose_name=_("Lot de publication"),
        null=True, blank=True,
        help_text=_(
            "Dernier lot dans lequel ce plan a été vu. C'est ce qui permet à la "
            "bascule de retirer les plans absents du lot sans avoir besoin d'un "
            "message de retrait. Un plan sans lot n'a été revu par aucune "
            "publication : il sera purgé à la prochaine bascule de son instance."
        ),
    )

    # ------------------------------------------------------------------ #
    # Identité
    # ------------------------------------------------------------------ #
    instance_id = models.CharField(
        _("Instance d'origine"), max_length=64, db_index=True,
        help_text=_("Déploiement CICADA qui a publié ce plan."),
    )
    id_pg = models.IntegerField(
        _("Identifiant du plan chez l'émetteur"),
        help_text=_(
            "Séquence locale de l'instance émettrice : n'a de sens que couplée "
            "à `instance_id`."
        ),
    )
    slug = models.SlugField(
        _("Slug"), max_length=255,
        help_text=_(
            "Slug du plan chez l'émetteur. Non unique ici : deux instances "
            "peuvent produire le même slug pour deux plans différents."
        ),
    )
    url_instance = models.URLField(
        _("URL publique de l'instance"), blank=True, default='',
        help_text=_(
            "Racine de l'instance émettrice, pour renvoyer l'utilisateur vers "
            "le plan chez lui quand c'est pertinent (édition, pièces jointes, "
            "données que le hub ne porte pas)."
        ),
    )

    # ------------------------------------------------------------------ #
    # Bandeau d'affichage
    # ------------------------------------------------------------------ #
    nom = models.CharField(_("Nom du plan"), max_length=500)
    statut = models.CharField(_("Statut"), max_length=20)
    rang = models.IntegerField(_("Rang"), null=True, blank=True)
    annee_debut = models.IntegerField(_("Année de début"), null=True, blank=True)
    annee_fin = models.IntegerField(_("Année de fin"), null=True, blank=True)
    type_document = models.CharField(
        _("Type de document"), max_length=255, null=True, blank=True,
    )
    gestionnaire_principal = models.CharField(
        _("Gestionnaire principal"), max_length=255, null=True, blank=True,
        help_text=_(
            "Nom de l'organisme, en clair. Faute d'identité nationale des "
            "organismes, seul le libellé voyage — il s'affiche, il ne filtre pas."
        ),
    )
    sites = models.JSONField(
        _("Sites"), default=list, blank=True,
        help_text=_(
            "Sites du plan tels qu'affichés sur une tuile : nom, slug et code "
            "INPN quand il existe."
        ),
    )
    sites_noms = models.TextField(
        _("Noms des sites"), blank=True, default='',
        help_text=_(
            "Noms des sites concaténés, pour la recherche par nom de site du "
            "mode « plan de gestion ». Dérivé de `sites` à l'ingestion : "
            "chercher dans un tableau JSON supposerait de le convertir en texte "
            "à chaque requête, sans pouvoir l'indexer."
        ),
    )

    # ------------------------------------------------------------------ #
    # Facettes
    # ------------------------------------------------------------------ #
    site_inpn_codes = ArrayField(
        models.CharField(max_length=50),
        verbose_name=_("Codes INPN des sites"), default=list, blank=True,
        help_text=_(
            "Stockés tels quels, et non traduits en identifiants locaux comme "
            "dans CICADA : le hub n'héberge aucun site, il n'a rien à quoi les "
            "apparier. C'est aussi ce qui permettra de dédoublonner un site "
            "co-géré par deux instances."
        ),
    )
    type_site_codes = ArrayField(
        models.CharField(max_length=25),
        verbose_name=_("Types d'aires protégées"), default=list, blank=True,
    )
    area_ids = ArrayField(
        models.IntegerField(),
        verbose_name=_("Zones géographiques"), default=list, blank=True,
        help_text=_(
            "Identifiants ref_geo **locaux au hub**, résolus à l'ingestion "
            "depuis les codes INSEE publiés."
        ),
    )
    organisme_codes = ArrayField(
        models.CharField(max_length=64),
        verbose_name=_("Organismes gestionnaires"), default=list, blank=True,
        help_text=_(
            "Vide tant que l'identité nationale des organismes n'est pas "
            "tranchée (SIRET ? annuaire RNF ?). La colonne existe pour que le "
            "filtre ait sa place le jour où la décision tombe : recopier un "
            "identifiant local ferait matcher le mauvais organisme, une "
            "corruption silencieuse, là où un tableau vide produit une absence "
            "visible."
        ),
    )

    # ------------------------------------------------------------------ #
    # Fiche publiée
    # ------------------------------------------------------------------ #
    fiche = models.JSONField(
        _("Fiche publique"), default=dict, blank=True,
        help_text=_(
            "Arbre rendu par les sérialiseurs de fiche de l'instance émettrice, "
            "stocké tel quel et resservi tel quel."
        ),
    )
    format_version = models.PositiveSmallIntegerField(
        _("Version du format d'échange"), default=0,
        help_text=_(
            "Version du contrat avec laquelle ce plan a été reçu. Les instances "
            "sont mises à jour indépendamment : deux plans du même hub peuvent "
            "venir de deux versions du format."
        ),
    )
    date_publication = models.DateTimeField(_("Publié le"), auto_now=True)

    class Meta:
        db_table = '"ccd_search"."t_plan_indexe"'
        verbose_name = _("Plan indexé")
        verbose_name_plural = _("Plans indexés")
        constraints = [
            models.UniqueConstraint(
                fields=['instance_id', 'id_pg'], name='uq_plan_indexe_origine',
            ),
        ]
        indexes = [
            models.Index(fields=['instance_id', 'slug'], name='idx_plan_instance_slug'),
            models.Index(fields=['statut'], name='idx_plan_statut'),
            # Recherche par nom de plan ou de site, tolérante aux fautes.
            GinIndex(
                fields=['nom'], name='idx_plan_nom_trgm',
                opclasses=['gin_trgm_ops'],
            ),
            GinIndex(
                fields=['sites_noms'], name='idx_plan_sites_noms_trgm',
                opclasses=['gin_trgm_ops'],
            ),
            GinIndex(fields=['area_ids'], name='idx_plan_areas'),
            GinIndex(fields=['type_site_codes'], name='idx_plan_types_site'),
            GinIndex(fields=['site_inpn_codes'], name='idx_plan_sites_inpn'),
        ]

    def __str__(self):
        return f"[{self.instance_id}] {self.nom}"


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
    # Identité
    # ------------------------------------------------------------------ #
    instance_id = models.CharField(
        _("Instance d'origine"), max_length=64, db_index=True,
    )
    type_contenu = models.CharField(
        _("Type de contenu"), max_length=20, choices=TYPE_CHOICES
    )
    id_objet = models.IntegerField(
        _("Identifiant de l'objet"),
        help_text=_("Clé primaire chez l'émetteur — séquence locale."),
    )
    plan = models.ForeignKey(
        PlanIndexe,
        on_delete=models.CASCADE,
        db_column='id_plan_indexe',
        related_name='contenus',
        verbose_name=_("Plan indexé"),
    )
    index_version = models.PositiveSmallIntegerField(
        _("Version des extracteurs"), default=0, db_index=True,
        help_text=_(
            "Version des extracteurs de l'instance émettrice qui a produit la "
            "ligne. Permet de repérer les instances en retard d'une version "
            "sans les interroger."
        ),
    )

    # ------------------------------------------------------------------ #
    # Texte recherché — mêmes poids et même configuration que CICADA
    # ------------------------------------------------------------------ #
    titre = models.CharField(_("Libellé"), max_length=500)
    description = models.TextField(_("Description"), blank=True, default='')
    rattachements = models.TextField(
        _("Objets rattachés"), blank=True, default='',
        help_text=_(
            "Espèces, habitats, éléments géologiques, protocoles standardisés, "
            "références PressRef et catégories d'action. Interrogé dans les DEUX "
            "modes de recherche."
        ),
    )
    contexte = models.TextField(
        _("Contexte"), blank=True, default='',
        help_text=_(
            "Libellés des objets ancêtres. Interrogé uniquement en mode élargi."
        ),
    )

    # ------------------------------------------------------------------ #
    # Affichage de la tuile
    # ------------------------------------------------------------------ #
    parent_type = models.CharField(
        _("Type du parent"), max_length=20, null=True, blank=True,
    )
    parent_libelle = models.CharField(
        _("Libellé du parent"), max_length=500, null=True, blank=True,
    )
    sous_type = models.CharField(
        _("Sous-type"), max_length=50, null=True, blank=True,
        help_text=_(
            "Code de la facette propre au type : `ecologique`/`socioeco` pour "
            "un enjeu, `ETAT`/`PRESSION`/`REPONSE` pour un indicateur, code de "
            "catégorie d'action pour une action."
        ),
    )
    sous_type_libelle = models.CharField(
        _("Libellé du sous-type"), max_length=255, null=True, blank=True,
    )

    # ------------------------------------------------------------------ #
    # Facettes du plan, redescendues sur la ligne
    # ------------------------------------------------------------------ #
    # Elles sont dupliquées depuis `PlanIndexe` **volontairement** : filtrer et
    # compter par facette est l'opération la plus fréquente de l'exploration, et
    # une jointure vers le plan sur chaque requête coûterait plus cher que ces
    # quelques colonnes. Elles sont réécrites à chaque publication du plan, donc
    # ne peuvent pas diverger longtemps.
    statut_pg = models.CharField(_("Statut du plan"), max_length=20)
    annee_debut = models.IntegerField(_("Année de début"), null=True, blank=True)
    annee_fin = models.IntegerField(_("Année de fin"), null=True, blank=True)
    type_site_codes = ArrayField(
        models.CharField(max_length=25),
        verbose_name=_("Types d'aires protégées"), default=list, blank=True,
    )
    area_ids = ArrayField(
        models.IntegerField(),
        verbose_name=_("Zones géographiques"), default=list, blank=True,
    )
    organisme_codes = ArrayField(
        models.CharField(max_length=64),
        verbose_name=_("Organismes gestionnaires"), default=list, blank=True,
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
    search_full = models.GeneratedField(
        expression=(
            SearchVector('titre', weight='A', config=SEARCH_CONFIG)
            + SearchVector('rattachements', weight='B', config=SEARCH_CONFIG)
            + SearchVector('description', weight='B', config=SEARCH_CONFIG)
            + SearchVector('contexte', weight='C', config=SEARCH_CONFIG)
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
            models.UniqueConstraint(
                fields=['instance_id', 'type_contenu', 'id_objet'],
                name='uq_recherche_contenu_objet',
            ),
        ]
        indexes = [
            GinIndex(fields=['search_titre'], name='idx_recherche_titre_gin'),
            GinIndex(fields=['search_full'], name='idx_recherche_full_gin'),
            # Tolérance aux fautes de frappe sur les libellés et sur les objets
            # rattachés : noms longs, souvent latins, rarement tapés sans faute.
            GinIndex(
                fields=['titre'], name='idx_recherche_titre_trgm',
                opclasses=['gin_trgm_ops'],
            ),
            GinIndex(
                fields=['rattachements'], name='idx_recherche_ratt_trgm',
                opclasses=['gin_trgm_ops'],
            ),
            GinIndex(fields=['type_site_codes'], name='idx_recherche_types_site'),
            GinIndex(fields=['area_ids'], name='idx_recherche_areas'),
            GinIndex(fields=['organisme_codes'], name='idx_recherche_organismes'),
            models.Index(fields=['type_contenu'], name='idx_recherche_type'),
            models.Index(fields=['statut_pg'], name='idx_recherche_statut'),
        ]

    def __str__(self):
        return f"[{self.instance_id}/{self.type_contenu}] {self.titre}"
