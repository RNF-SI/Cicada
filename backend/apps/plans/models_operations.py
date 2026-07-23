"""
Modèles pour les Opérations (Actions).
Hiérarchie : Métrique → Opération(s) (FK simple, une opération = une métrique)
"""
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class Protocole(models.Model):
    """
    Protocole associé à un suivi/inventaire.
    Contient les informations du protocole (Campanule) et les détails associés.
    """

    id_protocole = models.AutoField(primary_key=True)

    # Champs extraits de SuiviInventaire
    protocole_dans_campanule = models.BooleanField(
        _("Protocole répertorié dans Campanule"),
        null=True,
        blank=True,
        help_text=_("Le protocole est-il répertorié dans Campanule ?")
    )
    protocole_campanule_nom = models.CharField(
        _("Protocole (Campanule)"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Nom du protocole dans Campanule")
    )
    cd_protocole_campanule = models.IntegerField(
        _("Code protocole Campanule"),
        null=True,
        blank=True,
        help_text=_("Code du protocole dans le référentiel CAMPanule")
    )
    nb_etp_cycle = models.DecimalField(
        _("Nombre d'ETP par cycle"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Nombre d'ETP nécessaire par cycle de collecte")
    )
    respect_protocole = models.BooleanField(
        _("Respect strict du protocole"),
        null=True,
        blank=True,
        help_text=_("Respectez-vous strictement le protocole ?")
    )
    justification_non_respect = models.TextField(
        _("Justification non-respect"),
        blank=True,
        default='',
        help_text=_("Pourquoi ne respectez-vous pas le protocole ?")
    )
    differences_protocole = models.TextField(
        _("Différences avec le protocole"),
        blank=True,
        default='',
        help_text=_("Quelques différences avec le protocole ?")
    )

    nom_protocole = models.CharField(
        _("Nom du protocole"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Nom du protocole (si non Campanule)")
    )
    mode_validation = models.CharField(
        _("Mode et champ de validation"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("Mode et champ de validation du protocole")
    )

    # Nouveaux champs (Figma)
    description_protocole = models.TextField(
        _("Description du protocole"),
        blank=True,
        default='',
        help_text=_("Description du protocole (depuis Campanule)")
    )
    objectif_protocole = models.TextField(
        _("Objectif du protocole"),
        blank=True,
        default='',
        help_text=_("Détails de l'objectif du protocole")
    )
    periode_echantillonnage = models.CharField(
        _("Période d'échantillonnage"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Période d'échantillonnage du protocole")
    )

    # Champs ajoutés (Figma v2)
    periode_suivi = models.CharField(
        _("Période de suivi"),
        max_length=200,
        blank=True,
        default='',
        help_text=_("Mois de suivi (mnémoniques nomenclature PERIODE_SUIVI séparés par virgule, ex: 'JANVIER,FEVRIER,MARS')")
    )
    documentation_disponible = models.BooleanField(
        _("Documentation disponible"),
        null=True,
        blank=True,
        help_text=_("Une documentation décrivant le protocole est-elle disponible ?")
    )
    url_documentation = models.CharField(
        _("URL de la documentation"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("URL de la documentation du protocole")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_protocoles"'
        db_table_comment = "Protocoles associés aux suivis/inventaires"
        verbose_name = _("Protocole")
        verbose_name_plural = _("Protocoles")

    def __str__(self):
        return self.protocole_campanule_nom or f"Protocole #{self.id_protocole}"


class SuiviInventaire(models.Model):
    """
    Suivi ou inventaire associé à une opération.
    Contient les détails de la bancarisation et du suivi.
    Le protocole est dans une table dédiée (Protocole).
    """

    id_suivi_inventaire = models.AutoField(primary_key=True)

    # Champs standalone
    intitule = models.CharField(
        _("Intitulé"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("Nom affiché dans la liste des suivis/inventaires")
    )
    prix_indicatif = models.DecimalField(
        _("Prix indicatif (€/an)"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Prix indicatif en euros par an")
    )
    id_type_action = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis_type_action',
        db_column='id_type_action',
        verbose_name=_("Type d'action"),
        help_text=_("Code d'action CS associé (ex: CS8 = Inventaire de la faune)"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_ACTION'}
    )
    integre_plan_gestion = models.BooleanField(
        _("Intégré dans un plan de gestion"),
        null=True,
        blank=True,
        help_text=_("Ce suivi est-il intégré dans un plan de gestion ?")
    )
    id_pg = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis_inventaires',
        db_column='id_pg',
        verbose_name=_("Plan de gestion lié"),
        help_text=_("Plan de gestion associé (optionnel)")
    )
    suit_indicateur = models.BooleanField(
        _("Suit un indicateur"),
        null=True,
        blank=True,
        help_text=_("Le suivi/inventaire permet-il de suivre un indicateur ?")
    )
    type_indicateur = models.CharField(
        _("Type d'indicateur"),
        max_length=50,
        blank=True,
        default='',
        help_text=_("Type d'indicateur (mnémonique nomenclature TYPE_INDICATEUR : ETAT, PRESSION, REPONSE)")
    )
    cible_secondaire = models.CharField(
        _("Cible secondaire"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Cible secondaire du suivi/inventaire")
    )
    habitat_ref = models.CharField(
        _("Référentiel habitat"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("Référentiel habitat associé (noms, conservé pour l'affichage hérité)")
    )
    # Habitats structurés : liste de {cd_hab, lb_hab_fr}. Permet d'afficher les
    # correspondances EUNIS/Corine/Cahiers (qui nécessitent le cd_hab) — le champ
    # texte `habitat_ref` ci-dessus ne stockait que les noms.
    habitats = models.JSONField(
        _("Habitats (structurés)"),
        default=list,
        blank=True,
        help_text=_("Liste d'habitats HabRef : [{cd_hab, lb_hab_fr}, ...]")
    )
    id_statut = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis_statut',
        db_column='id_statut',
        verbose_name=_("Statut"),
        help_text=_("Statut du suivi (En cours, Terminé, A venir)"),
        limit_choices_to={'id_type__mnemonique': 'STATUT_SUIVI'}
    )
    actif = models.BooleanField(
        _("Actif"),
        default=True,
        help_text=_("Suivi actif ou inactif")
    )
    annee_fin_suivi = models.IntegerField(
        _("Année de fin du suivi"),
        null=True,
        blank=True,
        help_text=_("Année de fin du suivi")
    )
    frequence_nombre = models.IntegerField(
        _("Fréquence (nombre)"),
        null=True,
        blank=True,
        help_text=_("Nombre de répétitions")
    )
    frequence_unite = models.CharField(
        _("Fréquence (unité)"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Unité de fréquence (jour, semaine, mois, an)")
    )
    frequence_unite_precision = models.CharField(
        _("Précision fréquence (autre)"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Précision si fréquence 'Autre'")
    )
    commentaires = models.TextField(
        _("Commentaires"),
        blank=True,
        default='',
        help_text=_("Détails et commentaires")
    )

    # Détails de l'inventaire ou du suivi
    objectif_principal = models.CharField(
        _("Objectif principal"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Objectif principal de la collecte de données (mnémonique nomenclature OBJECTIF_SUIVI)")
    )
    objectif_secondaire = models.CharField(
        _("Objectif secondaire"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Objectif secondaire optionnel (mnémonique nomenclature OBJECTIF_SUIVI)")
    )
    cibles_principales = models.CharField(
        _("Cible principale"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Cible principale (mnémonique nomenclature CIBLE_SUIVI)")
    )
    taxon_taxref = models.CharField(
        _("Taxon - Taxref"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Référence taxon dans Taxref")
    )
    date_lancement_suivi = models.DateField(
        _("Date de lancement du suivi"),
        null=True,
        blank=True,
        help_text=_("Date de lancement du suivi")
    )

    # Protocoles (N-N vers table dédiée) — #252
    protocoles = models.ManyToManyField(
        Protocole,
        related_name='suivis',
        db_table='"general"."cor_suivi_protocole"',
        blank=True,
        verbose_name=_("Protocoles"),
        help_text=_("Protocoles associés au suivi/inventaire")
    )

    # Bancarisation et stockage
    outil_bancarisation = models.CharField(
        _("Outil de bancarisation"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Outil de bancarisation utilisé")
    )
    outil_saisie = models.CharField(
        _("Outil de saisie"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Existe t-il un outil de saisie ?")
    )
    transmission_donnee = models.BooleanField(
        _("Transmission de la donnée"),
        null=True,
        blank=True,
        help_text=_("Transmission de la donnée à l'organisme porteur ?")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_suivi_inventaires"'
        db_table_comment = "Suivis et inventaires associés aux opérations"
        verbose_name = _("Suivi / Inventaire")
        verbose_name_plural = _("Suivis / Inventaires")

    def __str__(self):
        return self.intitule or f"Suivi #{self.id_suivi_inventaire}"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_pg


def compute_code_prefix(categorie_action_reserve, type_action):
    """
    Préfixe 2 lettres utilisé pour calculer le code d'affichage d'une action.

    Priorité : `categorie_action_reserve.cd_nomenclature` (CT88, code 2 lettres
    comme SP/CS/IP/...). À défaut, on extrait les lettres de tête de
    `type_action.cd_nomenclature` (CS1.2 → 'CS', IP1 → 'IP'). Si aucun type
    n'est défini, retourne 'AC' (action) par sécurité.

    Fonction module (et non simple propriété) pour être appelable sur des
    valeurs non persistées : la prévisualisation du code avant enregistrement
    (#486) doit appliquer exactement la même règle que `Operation.code_prefix`.
    """
    if categorie_action_reserve is not None:
        code = (getattr(categorie_action_reserve, 'cd_nomenclature', '') or '').strip()
        if code:
            return code[:2].upper()
    if type_action is not None:
        code = (getattr(type_action, 'cd_nomenclature', '') or '').strip()
        if code:
            # Extraire les lettres de tête (CS1 → CS, IP1.1 → IP, SE → SE)
            letters = ''
            for ch in code:
                if ch.isalpha():
                    letters += ch
                else:
                    break
            if letters:
                return letters[:2].upper()
    return 'AC'


class Operation(models.Model):
    """
    Opération (action) rattachée à une métrique (FK simple).
    L'indicateur est déduit via metrique.id_indicateur.
    """

    id_operation = models.AutoField(primary_key=True)
    libelle = models.CharField(
        _("Libellé"),
        max_length=500,
        help_text=_("Intitulé de l'opération")
    )
    id_priorite = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_priorite',
        db_column='id_priorite',
        verbose_name=_("Priorité"),
        help_text=_("Niveau de priorité de l'opération"),
        limit_choices_to={'id_type__mnemonique': 'PRIORITE_OPERATION'}
    )
    id_type_action = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_type_action',
        db_column='id_type_action',
        verbose_name=_("Type d'action"),
        help_text=_("Type d'action (IP1, CS2, CI2, SP1, etc.). On utilise le référentiel d'Eden 62 en attendant l'élaboration du nouveau référentiel Gestref."),
        limit_choices_to={'id_type__mnemonique': 'TYPE_ACTION'}
    )
    # #228 / 2026-05-12 — Catégorie d'action réserve (CT88). Optionnel.
    # Si rempli, son préfixe (2 lettres) prend le pas sur celui de type_action
    # pour le calcul du code d'affichage (CS1, SP1, ...).
    id_categorie_action_reserve = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_categorie_reserve',
        db_column='id_categorie_action_reserve',
        verbose_name=_("Catégorie d'action réserve"),
        help_text=_("DOMAINES D'ACTIVITÉ réserve CT88"),
        limit_choices_to={'id_type__mnemonique': 'CATEGORIE_ACTION_RESERVE'},
    )
    id_referentiel_operations = models.CharField(
        _("Référentiel opérations"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Identifiant dans le référentiel d'opérations")
    )
    code_operation = models.CharField(
        _("Code opération"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Code de l'opération")
    )
    # #485 / #526 / #442 — Numéro fixé manuellement dans le code d'affichage
    # (le chiffre de « CS1 », « SP2 »…). NULL = numérotation automatique par
    # ordre de parcours du plan. Quand renseigné, ce numéro est réservé POUR SON
    # PRÉFIXE (ex. CS) : l'action le conserve quel que soit l'ordre (drag & drop),
    # et l'auto-numérotation des autres actions du même préfixe saute cet indice.
    numero_manuel = models.PositiveIntegerField(
        _("Numéro fixé manuellement"),
        null=True,
        blank=True,
        help_text=_("Numéro fixé manuellement dans le code (laisser vide pour la numérotation automatique)")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de l'opération")
    )
    annee_min = models.IntegerField(
        _("Année min"),
        null=True,
        blank=True,
        help_text=_("Année de début de l'opération")
    )
    annee_max = models.IntegerField(
        _("Année max"),
        null=True,
        blank=True,
        help_text=_("Année de fin de l'opération")
    )

    # Lien vers un suivi/inventaire existant
    est_suivi_existant = models.BooleanField(
        _("Inventaire ou suivi existant"),
        default=False,
        help_text=_("Inventaire ou suivi déjà saisi dans le module Mes inventaires et suivis ?")
    )
    id_suivi = models.ForeignKey(
        SuiviInventaire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations',
        db_column='id_suivi',
        verbose_name=_("Suivi / Inventaire lié"),
        help_text=_("Suivi ou inventaire associé à cette opération")
    )

    # Fréquence de l'action
    frequence_nombre = models.IntegerField(
        _("Fréquence (nombre)"),
        null=True,
        blank=True,
        help_text=_("Nombre de répétitions")
    )
    frequence_unite = models.CharField(
        _("Fréquence (unité)"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Unité de fréquence (jour, semaine, mois, an)")
    )

    # Acteurs
    operateurs = models.TextField(
        _("Opérateurs"),
        blank=True,
        null=True,
        help_text=_("Opérateurs de l'action")
    )
    partenaires = models.TextField(
        _("Partenaires"),
        blank=True,
        null=True,
        help_text=_("Partenaires de l'action")
    )
    financeurs = models.TextField(
        _("Financeurs"),
        blank=True,
        null=True,
        help_text=_("Financeurs de l'action")
    )

    # Programmation (JSON) - legacy
    programmation_annuelle = models.JSONField(
        _("Programmation annuelle"),
        default=dict,
        blank=True,
        help_text=_('Format: {"2024": true, "2025": false, ...}')
    )
    programmation_mensuelle = models.JSONField(
        _("Programmation mensuelle"),
        default=dict,
        blank=True,
        help_text=_('Format: {"2024": {"1": true, "2": false, ...}}')
    )

    # Template mensuel appliqué identiquement à toutes les années
    programmation_mensuelle_defaut = models.JSONField(
        _("Programmation mensuelle par défaut"),
        default=dict,
        blank=True,
        help_text=_('Template mensuel appliqué à toutes les années en mode récurrent. '
                     'Format: {"1": true, "2": false, ..., "12": true}')
    )

    # Mode de ventilation du budget
    VENTILATION_CHOICES = [
        ('none', _("Aucune")),
        ('by_org', _("Par organisme")),
        ('by_type', _("Par type de budget")),
        ('by_org_type', _("Par organisme et type de budget")),
        # #600 — modes « + type de poste » : même budget, mais le temps de
        # travail se décline par poste (remplace la case « Déclinaison par poste »).
        ('by_type_poste', _("Par type de budget et type de poste")),
        ('by_org_type_poste', _("Par organisme, type de budget et type de poste")),
    ]
    # Modes qui déclinent le temps de travail par poste (#600).
    VENTILATION_POSTE_MODES = ('by_type_poste', 'by_org_type_poste')

    ventilation_mode = models.CharField(
        _("Mode de ventilation"),
        max_length=30,
        choices=VENTILATION_CHOICES,
        default='none',
        help_text=_("Mode de ventilation du budget (aucune, par organisme, par type, les deux)")
    )
    declinaison_par_poste = models.BooleanField(
        _("Déclinaison par poste"),
        default=False,
        help_text=_("Détaille le temps de travail poste par poste (#560). Sinon "
                    "le temps est saisi par organisme quand le budget est "
                    "ventilé par organisme, et reste facultatif autrement.")
    )

    # Emprise spatiale (PostGIS)
    geom = models.GeometryField(
        _("Emprise spatiale"),
        srid=4326,
        null=True,
        blank=True,
        help_text=_("Emprise géographique de l'opération")
    )

    # #367 / #227 — Rattachement direct à un indicateur (état ou pression).
    # Permet de créer une action « dans l'indicateur » sans métrique préalable.
    # Le lien vers une/des métrique(s) (M2M ci-dessous) devient alors optionnel.
    id_indicateur = models.ForeignKey(
        'plans.Indicateur',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='operations',
        db_column='id_indicateur',
        verbose_name=_("Indicateur"),
        help_text=_("Indicateur (état ou pression) auquel l'action est rattachée, sans passer par une métrique")
    )

    # M2M vers Métriques (une opération peut être liée à plusieurs métriques)
    metriques = models.ManyToManyField(
        'plans.Metrique',
        through='CorOperationMetrique',
        related_name='operations',
        blank=True,
        verbose_name=_("Métriques"),
        help_text=_("Métriques associées à cette opération")
    )

    # M2M vers Site (zones d'application)
    sites = models.ManyToManyField(
        'users.Site',
        through='CorOperationSite',
        related_name='operations',
        blank=True
    )

    # #249 / #261 — Ordre d'affichage parmi les opérations d'une métrique.
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les opérations d'une métrique (0 = haut)")
    )

    # #251 — Statut éditorial : 'draft' tant que l'action n'a pas été validée
    # explicitement (tous les champs requis remplis via le bouton "Valider").
    # Permet d'afficher une chip "Brouillon" dans les listes.
    #
    # Default = 'valide' : c'est la valeur conservatrice (compatible avec le
    # comportement historique d'avant #251 et avec les opérations créées via
    # l'admin ou les seeders qui sont par construction "complètes"). Seul le
    # frontend (saveDraft) positionne explicitement 'draft'.
    STATUT_DRAFT = 'draft'
    STATUT_VALIDE = 'valide'
    STATUT_CHOICES = [
        (STATUT_DRAFT, _("Brouillon")),
        (STATUT_VALIDE, _("Validé")),
    ]
    statut = models.CharField(
        _("Statut"),
        max_length=10,
        choices=STATUT_CHOICES,
        default=STATUT_VALIDE,
        db_index=True,
        help_text=_("Brouillon tant que l'action n'a pas été validée explicitement")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_operations"'
        db_table_comment = "Opérations (actions) des plans de gestion"
        verbose_name = _("Opération")
        verbose_name_plural = _("Opérations")
        ordering = ['ordre', 'id_operation']

    def __str__(self):
        return self.libelle

    def get_plan_de_gestion(self):
        """
        Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248).
        Une opération est rattachée au plan via :
          - son suivi/inventaire (id_suivi → SuiviInventaire.id_pg) en priorité,
          - sinon une de ses métriques (M2M via CorOperationMetrique),
          - sinon son indicateur direct (id_indicateur, #367).
        Note : un suivi peut être orphelin (id_pg=None), auquel cas on
        retombe sur les métriques puis l'indicateur.
        """
        if self.id_suivi_id:
            try:
                plan = self.id_suivi.id_pg
                if plan is not None:
                    return plan
            except Exception:
                pass
        first_metrique = self.metriques.first() if hasattr(self, "metriques") else None
        if first_metrique is not None:
            return first_metrique.get_plan_de_gestion()
        # #367 — action rattachée directement à un indicateur (sans métrique)
        if self.id_indicateur_id:
            try:
                return self.id_indicateur.get_plan_de_gestion()
            except Exception:
                pass
        return None

    @property
    def code_prefix(self):
        """
        Préfixe 2 lettres utilisé pour calculer le code d'affichage.

        Délègue à `compute_code_prefix()` (#486 : la prévisualisation avant
        enregistrement doit appliquer exactement la même règle sur des valeurs
        de formulaire non encore persistées).
        """
        categorie = None
        if self.id_categorie_action_reserve_id:
            try:
                categorie = self.id_categorie_action_reserve
            except Exception:
                categorie = None
        type_action = None
        if self.id_type_action_id:
            try:
                type_action = self.id_type_action
            except Exception:
                type_action = None
        return compute_code_prefix(categorie, type_action)

    # #355 — Réalisation GLOBALE (sur toute la période du PG).
    # Libellés des niveaux (alignés sur la nomenclature NIVEAU_REALISATION) pour
    # exposer un libellé sans requête supplémentaire lors de la sérialisation.
    NIVEAU_REALISATION_LABELS = {
        'NON_DEMARRE': 'Non démarré',
        'EN_COURS': 'En cours',
        'PARTIEL': 'Partiel',
        'TERMINE': 'Terminé',
        'ABANDONNE': 'Abandonné',
        'REPORTE': 'Reporté',
        'NON_REALISE': 'Non réalisée',  # #379
    }

    def compute_niveau_realisation_global(self):
        """
        #355 — Calcule le niveau de réalisation GLOBAL d'une action sur la période,
        à partir des réalisations annuelles de ses années *programmées*.

        Années programmées = OperationAnnee avec periodicite=True (à défaut, toutes
        les années de l'opération). Règle :
          - aucune année programmée                       → None
          - aucune réalisation saisie                     → NON_DEMARRE
          - toutes les années programmées TERMINE         → TERMINE
          - uniquement ABANDONNE / uniquement REPORTE      → ABANDONNE / REPORTE
          - au moins une TERMINE/EN_COURS (mais pas toutes)→ EN_COURS
          - uniquement des PARTIEL                          → PARTIEL
          - sinon                                          → NON_DEMARRE

        Renvoie le mnémonique (str) ou None. Mapping volontairement conservateur :
        une action récurrente réalisée 1 an sur 10 reste « En cours », pas « Terminé ».
        """
        annees = list(self.operation_annees.all())
        programmed = [oa for oa in annees if oa.periodicite] or annees
        if not programmed:
            return None

        mnems = []
        for oa in programmed:
            real = getattr(oa, 'realisation', None)
            if real is not None and real.id_niveau_realisation_id:
                mnems.append(real.id_niveau_realisation.mnemonique)
            else:
                mnems.append(None)

        filled = [m for m in mnems if m]
        if not filled:
            return 'NON_DEMARRE'

        unique = set(filled)
        if filled and all(m == 'TERMINE' for m in mnems):
            return 'TERMINE'
        if unique == {'ABANDONNE'}:
            return 'ABANDONNE'
        if unique == {'REPORTE'}:
            return 'REPORTE'
        if unique == {'NON_REALISE'}:
            return 'NON_REALISE'  # #379 — toutes les années programmées non réalisées
        if unique <= {'NON_DEMARRE', 'NON_REALISE'}:
            # Ni progression ni terminaison : non réalisé si au moins une année
            # explicitement « non réalisée », sinon simplement non démarré.
            return 'NON_REALISE' if 'NON_REALISE' in unique else 'NON_DEMARRE'
        if 'TERMINE' in unique or 'EN_COURS' in unique:
            return 'EN_COURS'
        if 'PARTIEL' in unique:
            return 'PARTIEL'
        return 'NON_DEMARRE'

    @property
    def realisation_globale_override(self):
        """Objet OperationRealisationGlobale (surcharge manuelle) ou None."""
        return getattr(self, 'realisation_globale', None)

    def get_niveau_realisation_global(self):
        """
        Mnémonique effectif du niveau global : la surcharge manuelle si elle existe,
        sinon le calcul automatique (#355, statut hybride).
        """
        ov = self.realisation_globale_override
        if ov is not None and ov.id_niveau_realisation_id:
            return ov.id_niveau_realisation.mnemonique
        return self.compute_niveau_realisation_global()

    def get_niveau_realisation_global_label(self):
        """Libellé lisible du niveau global effectif (ou None)."""
        mnem = self.get_niveau_realisation_global()
        return self.NIVEAU_REALISATION_LABELS.get(mnem) if mnem else None

    def is_niveau_realisation_global_manuel(self):
        """True si le niveau global est issu d'une surcharge manuelle."""
        ov = self.realisation_globale_override
        return bool(ov is not None and ov.id_niveau_realisation_id)

    def get_niveau_realisation_global_commentaire(self):
        """Commentaire global de l'action (page globale) ou None (#356)."""
        ov = self.realisation_globale_override
        return ov.commentaire_override if ov else None


class CorOperationSite(models.Model):
    """
    Table de liaison entre Opérations et Sites (zones d'application).
    """

    id = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    id_site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        db_column='id_site',
        verbose_name=_("Site")
    )

    class Meta:
        db_table = '"general"."cor_operation_site"'
        db_table_comment = "Liaison opérations - sites"
        verbose_name = _("Opération - Site")
        verbose_name_plural = _("Opérations - Sites")
        unique_together = ['id_operation', 'id_site']

    def __str__(self):
        return f"Opération {self.id_operation_id} - Site {self.id_site_id}"


class CorOperationMetrique(models.Model):
    """
    Table de liaison entre Opérations et Métriques.
    """

    id = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    id_metrique = models.ForeignKey(
        'plans.Metrique',
        on_delete=models.CASCADE,
        db_column='id_metrique',
        verbose_name=_("Métrique")
    )

    class Meta:
        db_table = '"general"."cor_operation_metrique"'
        db_table_comment = "Liaison opérations - métriques"
        verbose_name = _("Opération - Métrique")
        verbose_name_plural = _("Opérations - Métriques")
        unique_together = ['id_operation', 'id_metrique']

    def __str__(self):
        return f"Opération {self.id_operation_id} - Métrique {self.id_metrique_id}"


class OperationAnnee(models.Model):
    """
    Programmation annuelle d'une opération.
    Une ligne par année entre annee_min et annee_max de l'opération.
    """

    id_operation_annee = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        related_name='operation_annees',
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    annee = models.IntegerField(_("Année"))
    periodicite = models.BooleanField(_("Périodicité"), default=False)
    budget = models.DecimalField(
        _("Budget prévisionnel (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    etp = models.DecimalField(
        _("Travail prévisionnel (jours)"),
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    budget_fonctionnement = models.DecimalField(
        _("Budget fonctionnement (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text=_("Utilisé en mode ventilation par type de budget (sans organismes)")
    )
    budget_investissement = models.DecimalField(
        _("Budget investissement (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text=_("Utilisé en mode ventilation par type de budget (sans organismes)")
    )
    periodicite_mensuelle = models.JSONField(
        _("Périodicité mensuelle"),
        default=dict, blank=True,
        help_text=_('Format: {"1": true, "2": false, ..., "12": true}')
    )
    geom = models.GeometryField(
        _("Emprise spatiale"),
        srid=4326, null=True, blank=True
    )

    class Meta:
        db_table = '"general"."t_operation_annees"'
        db_table_comment = "Programmation annuelle des opérations"
        verbose_name = _("Année d'opération")
        verbose_name_plural = _("Années d'opération")
        unique_together = ['id_operation', 'annee']
        ordering = ['annee']

    def __str__(self):
        return f"Opération {self.id_operation_id} - {self.annee}"


class OperationAnneeOrganisme(models.Model):
    """
    Ventilation budget/travail par organisme pour une année d'opération.
    """

    id_operation_annee_organisme = models.AutoField(primary_key=True)
    id_operation_annee = models.ForeignKey(
        OperationAnnee,
        on_delete=models.CASCADE,
        related_name='organismes',
        db_column='id_operation_annee',
        verbose_name=_("Année d'opération")
    )
    id_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.CASCADE,
        db_column='id_organisme',
        verbose_name=_("Organisme")
    )
    budget_fonctionnement = models.DecimalField(
        _("Budget fonctionnement (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    budget_investissement = models.DecimalField(
        _("Budget investissement (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    # #600 — coûts additionnels par organisme/année. Le coût salarial n'est pas
    # stocké : il se calcule (jours des postes × coût jour).
    cout_stage = models.DecimalField(
        _("Coût stage (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    cout_prestataire = models.DecimalField(
        _("Coût prestataire (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    autre_cout = models.DecimalField(
        _("Autre coût (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    autre_cout_commentaire = models.CharField(
        _("Commentaire autre coût"),
        max_length=255, blank=True, default=''
    )
    etp = models.DecimalField(
        _("Travail prévisionnel (jours)"),
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )

    class Meta:
        db_table = '"general"."t_operation_annee_organismes"'
        db_table_comment = "Ventilation budget/travail par organisme et par année"
        verbose_name = _("Organisme - Année d'opération")
        verbose_name_plural = _("Organismes - Années d'opération")
        unique_together = ['id_operation_annee', 'id_organisme']
        ordering = ['id_organisme__nom_organisme']

    def __str__(self):
        return f"OpAnnée {self.id_operation_annee_id} - Org {self.id_organisme_id}"


class FinanceOperation(models.Model):
    """
    Source de financement d'une opération.
    """

    id_finance_operation = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        related_name='finances',
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    libelle = models.CharField(_("Libellé"), max_length=255)
    id_categorie = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='finances_categorie',
        db_column='id_categorie',
        verbose_name=_("Catégorie de financement"),
        limit_choices_to={'id_type__mnemonique': 'CATEGORIE_FINANCE'}
    )

    class Meta:
        db_table = '"general"."t_finances_operations"'
        db_table_comment = "Sources de financement des opérations"
        verbose_name = _("Financement d'opération")
        verbose_name_plural = _("Financements d'opération")
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} (Opération {self.id_operation_id})"


class RealisationOperationAnnee(models.Model):
    """
    Suivi annuel de la réalisation d'une opération (1-1 avec OperationAnnee).
    Contient les valeurs réalisées au niveau de l'année :
      - niveau de réalisation, périodicité réalisée,
      - budget et travail réalisés quand la ventilation ne porte pas sur les organismes,
      - commentaires et emprise spatiale réalisée.
    Les valeurs ventilées par organisme sont stockées dans RealisationOperationAnneeOrganisme.
    """

    id_realisation_operation_annee = models.AutoField(primary_key=True)
    id_operation_annee = models.OneToOneField(
        OperationAnnee,
        on_delete=models.CASCADE,
        related_name='realisation',
        db_column='id_operation_annee',
        verbose_name=_("Année d'opération")
    )
    id_niveau_realisation = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='realisations_niveau',
        db_column='id_niveau_realisation',
        verbose_name=_("Niveau de réalisation"),
        limit_choices_to={'id_type__mnemonique': 'NIVEAU_REALISATION'}
    )
    periodicite_realisee = models.BooleanField(
        _("Périodicité réalisée"),
        default=False
    )
    periodicite_mensuelle_realisee = models.JSONField(
        _("Périodicité mensuelle réalisée"),
        default=dict,
        blank=True,
        help_text=_('Format: {"1": true, "2": false, ..., "12": true}')
    )
    commentaires = models.TextField(
        _("Détails / commentaires"),
        blank=True,
        null=True
    )
    geom_realisee = models.GeometryField(
        _("Emprise spatiale réalisée"),
        srid=4326,
        null=True,
        blank=True
    )
    budget_realise = models.DecimalField(
        _("Budget réalisé (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text=_("Utilisé quand ventilation_mode = 'none'")
    )
    budget_fonctionnement_realise = models.DecimalField(
        _("Budget fonctionnement réalisé (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text=_("Utilisé quand ventilation_mode = 'by_type' (sans organisme)")
    )
    budget_investissement_realise = models.DecimalField(
        _("Budget investissement réalisé (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text=_("Utilisé quand ventilation_mode = 'by_type' (sans organisme)")
    )
    etp_realise = models.DecimalField(
        _("Travail réalisé (jours)"),
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        help_text=_("Utilisé quand ventilation_mode ne porte pas sur les organismes")
    )
    # #541 — Opérateur(s) et financeur(s) RÉALISÉS pour l'année, distincts des
    # valeurs prévues portées par l'Operation. Saisis dans le suivi (par année).
    operateurs_realises = models.TextField(
        _("Opérateur(s) réalisé(s)"),
        blank=True,
        default='',
        help_text=_("Opérateur(s) ayant réellement conduit l'action cette année")
    )
    financeurs_realises = models.TextField(
        _("Financeur(s) réalisé(s)"),
        blank=True,
        default='',
        help_text=_("Financeur(s) et type de financement réellement mobilisés cette année")
    )
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_realisation_operation_annees"'
        db_table_comment = "Suivi de réalisation annuel d'une opération"
        verbose_name = _("Réalisation annuelle d'opération")
        verbose_name_plural = _("Réalisations annuelles d'opération")
        ordering = ['id_operation_annee__annee']

    def __str__(self):
        return f"Réalisation OpAnnée {self.id_operation_annee_id}"

    def get_plan_de_gestion(self):
        """Permet le scoping par plan via OperationAnnee → Operation."""
        try:
            return self.id_operation_annee.id_operation.get_plan_de_gestion()
        except Exception:
            return None


class RealisationOperationAnneeOrganisme(models.Model):
    """
    Ventilation par organisme des valeurs réalisées (1-1 avec OperationAnneeOrganisme).
    Utilisée quand ventilation_mode est 'by_org' ou 'by_org_type'.
    """

    id_realisation_op_annee_organisme = models.AutoField(primary_key=True)
    id_operation_annee_organisme = models.OneToOneField(
        OperationAnneeOrganisme,
        on_delete=models.CASCADE,
        related_name='realisation',
        db_column='id_operation_annee_organisme',
        verbose_name=_("Organisme - Année d'opération")
    )
    budget_fonctionnement_realise = models.DecimalField(
        _("Budget fonctionnement réalisé (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    budget_investissement_realise = models.DecimalField(
        _("Budget investissement réalisé (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    etp_realise = models.DecimalField(
        _("Travail réalisé (jours)"),
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)

    class Meta:
        db_table = '"general"."t_realisation_operation_annee_organismes"'
        db_table_comment = "Ventilation par organisme du suivi de réalisation annuel"
        verbose_name = _("Réalisation par organisme - Année d'opération")
        verbose_name_plural = _("Réalisations par organisme - Années d'opération")

    def __str__(self):
        return f"Réalisation OrgAnnée {self.id_operation_annee_organisme_id}"

    def get_plan_de_gestion(self):
        """Permet le scoping par plan via OperationAnneeOrganisme."""
        try:
            return (
                self.id_operation_annee_organisme
                .id_operation_annee
                .id_operation
                .get_plan_de_gestion()
            )
        except Exception:
            return None


class OperationRealisationGlobale(models.Model):
    """
    #355 — Surcharge MANUELLE du niveau de réalisation global d'une action
    (sur toute la période du PG). 1-1 avec Operation.

    En l'absence de cette ligne, le niveau global est calculé automatiquement
    (Operation.compute_niveau_realisation_global). Quand un gestionnaire force
    un statut (action faite en avance/retard, ou « terminée » malgré une session
    manquante), on enregistre la surcharge ici. C'est de la donnée de SUIVI :
    elle reste éditable après validation du plan (pas de verrou brouillon),
    comme RealisationOperationAnnee.
    """

    id_operation_realisation_globale = models.AutoField(primary_key=True)
    id_operation = models.OneToOneField(
        Operation,
        on_delete=models.CASCADE,
        related_name='realisation_globale',
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    id_niveau_realisation = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='realisations_globales_niveau',
        db_column='id_niveau_realisation',
        verbose_name=_("Niveau de réalisation global (surcharge)"),
        limit_choices_to={'id_type__mnemonique': 'NIVEAU_REALISATION'}
    )
    commentaire_override = models.TextField(
        _("Commentaire de surcharge"),
        blank=True,
        null=True
    )
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_operation_realisation_globale"'
        db_table_comment = "Surcharge manuelle du niveau de réalisation global d'une action (#355)"
        verbose_name = _("Réalisation globale d'opération")
        verbose_name_plural = _("Réalisations globales d'opération")

    def __str__(self):
        return f"Réalisation globale Opération {self.id_operation_id}"

    def get_plan_de_gestion(self):
        """Permet le scoping par plan via Operation."""
        try:
            return self.id_operation.get_plan_de_gestion()
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Ressources humaines (#560) — postes/fonctions, personnes du PG et saisie du
# temps de travail par poste/personne avec distinction financé / non financé.
# Remplace la saisie plate « Travail prévisionnel (jours) » (OperationAnnee.etp)
# par des lignes RH détaillées, au prévisionnel comme au réel (suivi).
# ---------------------------------------------------------------------------


class Fonction(models.Model):
    """
    Fonction / poste type d'une réserve (conservateur, garde, animateur,
    écovolontaire, bénévole…). Référentiel **global** partagé par tous les
    plans, seedé depuis un socle et librement complétable à la volée (#560).

    Le caractère financé / non financé par défaut est porté par la fonction,
    mais reste surchargeable à chaque saisie de temps (cf. OperationAnneeRH).
    """

    # Type de poste porté par la fonction (#596) : conditionne la saisie du
    # coût jour dans la fiche action / le dialog poste.
    TYPE_SALARIE = 'salarie'
    TYPE_STAGIAIRE = 'stagiaire'
    TYPE_PRESTATAIRE = 'prestataire'
    TYPE_BENEVOLE = 'benevole'
    TYPE_POSTE_CHOICES = [
        (TYPE_SALARIE, _("Salarié")),
        (TYPE_STAGIAIRE, _("Stagiaire")),
        (TYPE_PRESTATAIRE, _("Prestataire")),
        (TYPE_BENEVOLE, _("Bénévole")),
    ]

    id_fonction = models.AutoField(primary_key=True)
    libelle = models.CharField(_("Libellé"), max_length=150, unique=True)
    type_poste = models.CharField(
        _("Type de poste"),
        max_length=20,
        choices=TYPE_POSTE_CHOICES,
        default=TYPE_SALARIE,
        help_text=_("Catégorie de la fonction. Conditionne la saisie du coût "
                    "jour : pas de coût jour pour un prestataire, 0 par défaut "
                    "pour un bénévole.")
    )
    finance_par_defaut = models.BooleanField(
        _("Financé par défaut"),
        default=True,
        help_text=_("Valeur par défaut du caractère financé pour cette fonction "
                    "(surchargeable à chaque saisie de temps)")
    )
    is_socle = models.BooleanField(
        _("Fonction du socle"),
        default=False,
        help_text=_("Fonction issue du socle de référence (protégée en suppression)")
    )
    actif = models.BooleanField(_("Active"), default=True)
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)

    class Meta:
        db_table = '"general"."t_fonctions"'
        db_table_comment = "Référentiel global des fonctions/postes (#560)"
        verbose_name = _("Fonction")
        verbose_name_plural = _("Fonctions")
        ordering = ['libelle']

    def __str__(self):
        return self.libelle

    def demande_cout_jour(self):
        """Un prestataire ne se saisit pas au coût jour (coût forfaitaire)."""
        return self.type_poste != self.TYPE_PRESTATAIRE

    def cout_jour_defaut(self):
        """Coût jour proposé par défaut : 0 pour un bénévole, sinon rien."""
        return 0 if self.type_poste == self.TYPE_BENEVOLE else None


class Poste(models.Model):
    """
    Poste d'un plan de gestion (#560).

    **Aucune donnée nominative** (RGPD) : on décrit des postes, pas des
    personnes. Un poste représente un type d'emploi du PG, en `nombre`
    exemplaires (ex. 3 stagiaires) pour une enveloppe de `etp` ETP au total,
    rattaché à un organisme.

    Le poste porte une ou plusieurs fonctions (cf. PosteFonction) :

    - **sans quotité** → poste combiné : un « garde animateur » à 1 ETP cumule
      les deux casquettes sur l'ensemble de son temps ;
    - **avec quotités** → répartition explicite du temps (50 % garde /
      50 % animateur), dont la somme doit faire 100 %.
    """

    id_poste = models.AutoField(primary_key=True)
    id_pg = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.CASCADE,
        related_name='postes',
        db_column='id_pg',
        verbose_name=_("Plan de gestion")
    )
    id_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='postes',
        db_column='id_organisme',
        verbose_name=_("Organisme"),
        help_text=_("Organisme employeur / porteur du poste")
    )
    organisme_libre = models.CharField(
        _("Organisme (saisi)"),
        max_length=150,
        blank=True,
        default='',
        help_text=_("Nom d'organisme saisi librement, hors référentiel — "
                    "notamment pour un prestataire (ex. « presta1 »). Facultatif.")
    )
    nombre = models.PositiveSmallIntegerField(
        _("Nombre de postes"),
        default=1,
        help_text=_("Combien de postes de ce type (ex. 3 stagiaires)")
    )
    etp = models.DecimalField(
        _("ETP total"),
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text=_("Nombre d'ETP pour ce poste, TOTAL sur les `nombre` postes")
    )
    cout_jour = models.DecimalField(
        _("Coût jour (€)"),
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text=_("Coût journalier du poste (€), utilisé pour le calcul du "
                    "coût salarial. Vide pour un prestataire (coût forfaitaire), "
                    "0 pour un bénévole.")
    )
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)

    class Meta:
        db_table = '"general"."t_postes"'
        db_table_comment = "Postes d'un plan de gestion, sans nominatif (#560)"
        verbose_name = _("Poste du plan")
        verbose_name_plural = _("Postes du plan")
        ordering = ['id_poste']

    def __str__(self):
        return self.libelle or f"Poste {self.pk}"

    @property
    def libelle(self):
        """
        Libellé dérivé des fonctions : « Garde · Animateur » (poste combiné)
        ou « Garde 50 % · Animateur 50 % » (quotités explicites).
        """
        parts = []
        for pf in self.fonctions.all():
            if pf.pourcentage is None:
                parts.append(pf.id_fonction.libelle)
            else:
                pct = pf.pourcentage.normalize()
                parts.append(f"{pf.id_fonction.libelle} {pct:f} %")
        return ' · '.join(parts)

    def is_finance_par_defaut(self):
        """
        Un poste est financé par défaut sauf si TOUTES ses fonctions sont non
        financées (bénévole, écovolontaire…). Sert de valeur initiale aux
        lignes RH, qui restent surchargeables.
        """
        fonctions = [pf.id_fonction for pf in self.fonctions.all()]
        if not fonctions:
            return True
        return any(f.finance_par_defaut for f in fonctions)

    def is_prestataire(self):
        """Vrai si au moins une fonction du poste est de type prestataire (#599)."""
        return any(
            pf.id_fonction.type_poste == Fonction.TYPE_PRESTATAIRE
            for pf in self.fonctions.all()
        )

    @property
    def organisme_affichage(self):
        """Organisme à afficher : le référentiel s'il existe, sinon la saisie libre."""
        if self.id_organisme_id:
            return self.id_organisme.nom_organisme
        return self.organisme_libre or None

    def get_plan_de_gestion(self):
        """Permet le scoping par plan (#248)."""
        try:
            return self.id_pg
        except Exception:
            return None


class PosteFonction(models.Model):
    """
    Fonction portée par un poste, avec une quotité facultative (#560).

    Quotité NULL = la fonction s'applique à tout le temps du poste (cumul de
    casquettes). Quotité renseignée = part explicite du temps ; la somme des
    quotités d'un poste doit alors valoir 100 %.
    """

    id_poste_fonction = models.AutoField(primary_key=True)
    id_poste = models.ForeignKey(
        Poste,
        on_delete=models.CASCADE,
        related_name='fonctions',
        db_column='id_poste',
        verbose_name=_("Poste")
    )
    id_fonction = models.ForeignKey(
        Fonction,
        on_delete=models.PROTECT,
        related_name='postes',
        db_column='id_fonction',
        verbose_name=_("Fonction")
    )
    pourcentage = models.DecimalField(
        _("Quotité (%)"),
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text=_("Part de temps sur cette fonction (0 à 100). Laisser vide "
                    "pour un poste qui cumule les fonctions sur tout son temps.")
    )

    class Meta:
        db_table = '"general"."cor_poste_fonction"'
        db_table_comment = "Fonctions portées par un poste du PG (#560)"
        verbose_name = _("Fonction d'un poste")
        verbose_name_plural = _("Fonctions d'un poste")
        unique_together = ['id_poste', 'id_fonction']
        ordering = ['id_fonction__libelle']

    def __str__(self):
        return f"{self.id_poste_id} - {self.id_fonction_id}"

    def get_plan_de_gestion(self):
        try:
            return self.id_poste.get_plan_de_gestion()
        except Exception:
            return None


class CategorieDepense:
    """
    Catégorie de dépense d'une ligne de temps de travail (#597).

    Remplace, côté saisie, le booléen « Financé » : « Bénévolat partenariat »
    correspond au temps non financé, le reste au temps financé. Le booléen
    `finance` est conservé (dérivé) pour toute la logique d'agrégation existante.
    """
    FONCTIONNEMENT = 'fonctionnement'
    INVESTISSEMENT = 'investissement'
    BENEVOLAT_PARTENARIAT = 'benevolat_partenariat'
    CHOICES = [
        (FONCTIONNEMENT, _("Fonctionnement")),
        (INVESTISSEMENT, _("Investissement")),
        (BENEVOLAT_PARTENARIAT, _("Bénévolat partenariat")),
    ]

    @classmethod
    def resolve(cls, categorie, finance):
        """
        Réconcilie (categorie_depense, finance). La catégorie prime ; à défaut
        (écritures legacy / import qui ne posent que `finance`), elle est
        dérivée du booléen. Retourne le couple (categorie, finance) cohérent.
        """
        if categorie:
            return categorie, categorie != cls.BENEVOLAT_PARTENARIAT
        finance = True if finance is None else bool(finance)
        return (cls.FONCTIONNEMENT if finance else cls.BENEVOLAT_PARTENARIAT), finance


class _RhLigneBase(models.Model):
    """
    Base abstraite des lignes RH (prév. / réel) : porte la catégorie de
    dépense (#597) et garantit sa cohérence avec le booléen `finance` (défini
    par les modèles concrets) à chaque `save()`.
    """
    categorie_depense = models.CharField(
        _("Catégorie de dépense"),
        max_length=30,
        choices=CategorieDepense.CHOICES,
        blank=True, default='',
        help_text=_("Catégorie budgétaire de la ligne. « Bénévolat partenariat » "
                    "correspond au temps non financé.")
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.categorie_depense, self.finance = CategorieDepense.resolve(
            self.categorie_depense, self.finance
        )
        super().save(*args, **kwargs)


class OperationAnneeRH(_RhLigneBase):
    """
    Ligne de temps de travail **prévisionnel** d'une année d'opération (#560).

    La cible dépend du mode d'affichage de l'action :

    - **déclinaison par poste** (`Operation.declinaison_par_poste`) → une ligne
      par poste du PG (`id_poste`) ;
    - **ventilation budgétaire par organisme** → une ligne par organisme
      (`id_organisme`) ;
    - sinon → ligne sans cible (temps global, saisie facultative).

    Le caractère financé / non financé est initialisé depuis les fonctions du
    poste mais reste surchargeable ici. Remplace le champ plat
    OperationAnnee.etp.
    """

    id_operation_annee_rh = models.AutoField(primary_key=True)
    id_operation_annee = models.ForeignKey(
        OperationAnnee,
        on_delete=models.CASCADE,
        related_name='rh_lignes',
        db_column='id_operation_annee',
        verbose_name=_("Année d'opération")
    )
    id_poste = models.ForeignKey(
        Poste,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rh_lignes_prev',
        db_column='id_poste',
        verbose_name=_("Poste")
    )
    id_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rh_lignes_prev',
        db_column='id_organisme',
        verbose_name=_("Organisme")
    )
    jours = models.DecimalField(
        _("Nombre de jours"),
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    finance = models.BooleanField(_("Financé"), default=True)

    class Meta:
        db_table = '"general"."t_operation_annee_rh"'
        db_table_comment = "Lignes RH prévisionnelles par année d'opération (#560)"
        verbose_name = _("Ligne RH prévisionnelle")
        verbose_name_plural = _("Lignes RH prévisionnelles")
        ordering = ['id_operation_annee_rh']

    def __str__(self):
        return f"RH prév OpAnnée {self.id_operation_annee_id} ({self.jours} j)"

    def get_plan_de_gestion(self):
        """Permet le scoping par plan via OperationAnnee → Operation (#248)."""
        try:
            return self.id_operation_annee.id_operation.get_plan_de_gestion()
        except Exception:
            return None


class RealisationOperationAnneeRH(_RhLigneBase):
    """
    Ligne de temps de travail **réalisé** d'une année d'opération (#560),
    saisie au moment du suivi. Miroir de OperationAnneeRH côté réel : permet
    de préciser quel poste (ou quel organisme) a réellement conduit l'action
    et pour quel temps effectif, financé ou non.
    """

    id_realisation_operation_annee_rh = models.AutoField(primary_key=True)
    id_realisation_operation_annee = models.ForeignKey(
        RealisationOperationAnnee,
        on_delete=models.CASCADE,
        related_name='rh_lignes',
        db_column='id_realisation_operation_annee',
        verbose_name=_("Réalisation annuelle d'opération")
    )
    id_operation_annee_rh = models.ForeignKey(
        OperationAnneeRH,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='realisations',
        db_column='id_operation_annee_rh',
        verbose_name=_("Ligne prévisionnelle réalisée"),
        help_text=_(
            "Ligne RH prévisionnelle que cette saisie réalise. Conserve le lien "
            "prévu ↔ réel même quand le poste (ou l'organisme) ayant réellement "
            "conduit l'action diffère de celui prévu. NULL pour un temps réalisé "
            "qui n'était pas prévu."
        )
    )
    id_poste = models.ForeignKey(
        Poste,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rh_lignes_reel',
        db_column='id_poste',
        verbose_name=_("Poste")
    )
    id_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rh_lignes_reel',
        db_column='id_organisme',
        verbose_name=_("Organisme")
    )
    jours = models.DecimalField(
        _("Nombre de jours réalisés"),
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    finance = models.BooleanField(_("Financé"), default=True)

    class Meta:
        db_table = '"general"."t_realisation_operation_annee_rh"'
        db_table_comment = "Lignes RH réalisées par année d'opération (#560)"
        verbose_name = _("Ligne RH réalisée")
        verbose_name_plural = _("Lignes RH réalisées")
        ordering = ['id_realisation_operation_annee_rh']

    def __str__(self):
        return f"RH réel RéalOpAnnée {self.id_realisation_operation_annee_id} ({self.jours} j)"

    def get_plan_de_gestion(self):
        """Permet le scoping par plan via RealisationOperationAnnee (#248)."""
        try:
            return self.id_realisation_operation_annee.get_plan_de_gestion()
        except Exception:
            return None
