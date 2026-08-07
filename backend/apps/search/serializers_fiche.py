"""
Sérialiseurs de la fiche publique d'un plan de gestion.

**Ces sérialiseurs sont volontairement écrits à la main, sans réutiliser ceux
de `apps.plans`.** La fiche est consultable par tout utilisateur connecté, y
compris hors de l'organisme gestionnaire : c'est le seul endroit du projet où
le contenu d'un plan sort de son périmètre de lecture (#610). Hériter des
sérialiseurs internes ferait entrer ici, à la première évolution de ceux-ci,
des champs que personne n'aurait décidé de publier.

Périmètre publié : la **structure** du plan — enjeux, facteurs d'influence,
pressions, objectifs, niveaux d'exigence, résultats attendus, indicateurs,
métriques et actions programmées, avec pour chaque action son suivi
(objectifs, espèces et habitats ciblés, fréquence, outils), ses protocoles et
ses indicateurs de réponse.

Périmètre exclu, et la liste est exhaustive :

- budget et financement (``OperationAnnee``, ``FinanceOperation``,
  ``Operation.financeurs``) ;
- ressources humaines (``Poste``, ``Fonction``, ``OperationAnneeRH``) ;
- données empiriques : mesures d'indicateurs (``Mesure``) et réalisations
  annuelles (``RealisationOperationAnnee``) ;
- traçabilité interne : auteurs et dates de modification.

Le test `TestFichePubliqueCloisonnement` vérifie ces exclusions champ par champ.
"""

from rest_framework import serializers


def _label(nomenclature):
    return nomenclature.label if nomenclature else None


#: Libellés des 5 paliers de la grille de lecture, dans l'ordre des scores.
NIVEAUX_GRILLE = {
    1: "Très mauvais", 2: "Mauvais", 3: "Moyen", 4: "Bon", 5: "Très bon",
}


class MetriquePubliqueSerializer(serializers.Serializer):
    """Définition d'une métrique — ce qui est mesuré, jamais les mesures."""

    id_metrique = serializers.IntegerField()
    nom_metrique = serializers.CharField()
    unite = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    grille = serializers.SerializerMethodField()

    def get_grille(self, metrique):
        """
        Grille de lecture 5 paliers, ou `None` si la métrique n'en a pas (#634).

        C'est le barème d'évaluation — ce qui fait qu'une mesure vaut « bon »
        plutôt que « moyen ». Il est publié parce qu'une valeur seule ne se lit
        pas sans lui ; les mesures, elles, restent internes.

        Le rendu textuel des paliers (intervalles, bornes incluses, blocs ET/OU)
        vient de l'export de fiche action : c'est la source de vérité de cette
        notation, et deux implémentations divergeraient (#619).
        """
        from apps.plans.services_export_fiche_action import _grid_cell, _is_grille

        if not _is_grille(metrique):
            return None
        paliers = [
            {'niveau': niveau, 'libelle': libelle,
             'valeur': _grid_cell(metrique, niveau) or None}
            for niveau, libelle in NIVEAUX_GRILLE.items()
        ]
        # Une grille dont aucun palier n'est renseigné n'apprend rien : on la
        # tait plutôt que d'afficher cinq cases vides.
        return paliers if any(p['valeur'] for p in paliers) else None


class IndicateurPublicSerializer(serializers.Serializer):
    id_indicateur = serializers.IntegerField()
    nom_indicateur = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    type_indicateur = serializers.SerializerMethodField()
    est_standardise = serializers.BooleanField()
    metriques = MetriquePubliqueSerializer(many=True)

    def get_type_indicateur(self, indicateur):
        return _label(indicateur.type_indicateur)


def _texte(valeur):
    """Chaîne non vide, ou `None` — pour ne pas publier des champs à `''`."""
    valeur = (valeur or '').strip()
    return valeur or None


class ProtocolePublicSerializer(serializers.Serializer):
    """
    Protocole d'un suivi : comment la donnée est collectée.

    Le nom vient de CAMPanule pour un protocole standardisé, de la saisie libre
    sinon — la distinction est portée par `standardise`, comme dans l'export de
    fiche action. `respecte`/`justification_non_respect` sont publiés parce
    qu'un protocole appliqué avec des écarts ne se compare pas à un protocole
    appliqué à la lettre : c'est ce qui rend la donnée interprétable de
    l'extérieur.

    Exclu : `nb_etp_cycle`, qui est de la charge de travail, donc du RH.
    """

    id_protocole = serializers.IntegerField()
    standardise = serializers.BooleanField(
        source='protocole_dans_campanule', allow_null=True)
    nom = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    objectif = serializers.SerializerMethodField()
    respecte = serializers.BooleanField(
        source='respect_protocole', allow_null=True)
    justification_non_respect = serializers.SerializerMethodField()
    differences = serializers.SerializerMethodField()
    periode_echantillonnage = serializers.SerializerMethodField()
    periode_suivi = serializers.SerializerMethodField()
    mode_validation = serializers.SerializerMethodField()
    documentation_disponible = serializers.BooleanField(allow_null=True)
    url_documentation = serializers.SerializerMethodField()

    def get_nom(self, protocole):
        """Le nom CAMPanule prime, avec repli sur la saisie libre (et vice-versa)."""
        if protocole.protocole_dans_campanule:
            return (_texte(protocole.protocole_campanule_nom)
                    or _texte(protocole.nom_protocole))
        return (_texte(protocole.nom_protocole)
                or _texte(protocole.protocole_campanule_nom))

    def get_description(self, protocole):
        return _texte(protocole.description_protocole)

    def get_objectif(self, protocole):
        return _texte(protocole.objectif_protocole)

    def get_justification_non_respect(self, protocole):
        return _texte(protocole.justification_non_respect)

    def get_differences(self, protocole):
        return _texte(protocole.differences_protocole)

    def get_periode_echantillonnage(self, protocole):
        return _texte(protocole.periode_echantillonnage)

    def get_mode_validation(self, protocole):
        return _texte(protocole.mode_validation)

    def get_url_documentation(self, protocole):
        return _texte(protocole.url_documentation)

    def get_periode_suivi(self, protocole):
        """Mois de suivi : mnémoniques en base, libellés en sortie."""
        libelles = getattr(protocole, 'libelles_pub', {})
        return [
            libelles.get(('PERIODE_SUIVI', mnemonique), mnemonique)
            for mnemonique in (protocole.periode_suivi or '').split(',')
            if mnemonique.strip()
        ]


class SuiviPublicSerializer(serializers.Serializer):
    """
    Suivi ou inventaire porté par une action de connaissance.

    C'est lui qui dit **ce qui est observé** — l'espèce, l'habitat, l'objectif
    de la collecte — et **comment** : fréquence, outils de saisie et de
    bancarisation, protocoles. Sans ce bloc, une action « CS » se lit comme un
    intitulé sans contenu (#634).

    Les champs `objectif_*`, `cible_*` et les outils stockent des mnémoniques
    de nomenclature : ils sont résolus en libellés par `fiche.py`, en une
    requête pour toute la fiche.
    """

    id_suivi = serializers.IntegerField(source='id_suivi_inventaire')
    intitule = serializers.CharField()
    statut = serializers.SerializerMethodField()
    actif = serializers.BooleanField()
    objectif_principal = serializers.SerializerMethodField()
    objectif_secondaire = serializers.SerializerMethodField()
    cible_principale = serializers.SerializerMethodField()
    cible_secondaire = serializers.SerializerMethodField()
    taxon = serializers.SerializerMethodField()
    habitats = serializers.SerializerMethodField()
    frequence = serializers.SerializerMethodField()
    annee_fin_suivi = serializers.IntegerField(allow_null=True)
    date_lancement = serializers.DateField(
        source='date_lancement_suivi', allow_null=True)
    outil_saisie = serializers.SerializerMethodField()
    outil_bancarisation = serializers.SerializerMethodField()
    transmission_donnee = serializers.BooleanField(allow_null=True)
    commentaires = serializers.SerializerMethodField()
    protocoles = ProtocolePublicSerializer(many=True)

    def _libelle(self, suivi, type_mnemonique, mnemonique):
        mnemonique = (mnemonique or '').strip()
        if not mnemonique:
            return None
        libelles = getattr(suivi, 'libelles_pub', {})
        return libelles.get((type_mnemonique, mnemonique), mnemonique)

    def get_statut(self, suivi):
        return _label(suivi.id_statut)

    def get_objectif_principal(self, suivi):
        return self._libelle(suivi, 'OBJECTIF_SUIVI', suivi.objectif_principal)

    def get_objectif_secondaire(self, suivi):
        return self._libelle(suivi, 'OBJECTIF_SUIVI', suivi.objectif_secondaire)

    def get_cible_principale(self, suivi):
        return self._libelle(suivi, 'CIBLE_SUIVI', suivi.cibles_principales)

    def get_cible_secondaire(self, suivi):
        return self._libelle(suivi, 'CIBLE_SUIVI', suivi.cible_secondaire)

    def get_outil_saisie(self, suivi):
        return self._libelle(suivi, 'OUTIL_SAISIE', suivi.outil_saisie)

    def get_outil_bancarisation(self, suivi):
        return self._libelle(
            suivi, 'BANCARISATION_STOCKAGE', suivi.outil_bancarisation)

    def get_commentaires(self, suivi):
        return _texte(suivi.commentaires)

    def get_taxon(self, suivi):
        return _texte(suivi.taxon_taxref)

    def get_habitats(self, suivi):
        """
        Habitats ciblés, structurés quand ils viennent de HabRef.

        `habitats` (JSON) est la forme moderne ; `habitat_ref` est l'ancien
        champ texte, encore seul renseigné sur les suivis d'avant #368. On
        publie le premier s'il existe, et on retombe sur le second.
        """
        structures = [
            {'cd_hab': habitat.get('cd_hab'),
             'lb_hab_fr': habitat.get('lb_hab_fr')}
            for habitat in (suivi.habitats or [])
            if isinstance(habitat, dict) and (
                habitat.get('cd_hab') or habitat.get('lb_hab_fr'))
        ]
        if structures:
            return structures
        herite = _texte(suivi.habitat_ref)
        return [{'cd_hab': None, 'lb_hab_fr': herite}] if herite else []

    def get_frequence(self, suivi):
        """« 2 par an », ou la précision libre quand l'unité est « Autre »."""
        precision = _texte(suivi.frequence_unite_precision)
        unite = _texte(suivi.frequence_unite) or precision
        if suivi.frequence_nombre and unite:
            return f"{suivi.frequence_nombre} / {unite}"
        return unite or (
            str(suivi.frequence_nombre) if suivi.frequence_nombre else None)


class ActionPubliqueSerializer(serializers.Serializer):
    """
    Action de gestion, sans sa dimension financière ni sa réalisation.

    `annee_min`/`annee_max` disent quand l'action est programmée ; le détail
    annuel (budget, ETP, ventilation par organisme) reste interne.

    Les indicateurs de **réponse** sont sortis du cadre et publiés à part, comme
    dans l'export de fiche action (#626) : ils mesurent l'effet de l'action, pas
    l'état ou la pression qu'elle sert, et les mélanger rendait la ligne
    « Indicateur » illisible.
    """

    id_operation = serializers.IntegerField()
    libelle = serializers.CharField()
    code_operation = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    categorie = serializers.SerializerMethodField()
    type_action = serializers.SerializerMethodField()
    priorite = serializers.SerializerMethodField()
    annee_min = serializers.IntegerField(allow_null=True)
    annee_max = serializers.IntegerField(allow_null=True)
    frequence = serializers.SerializerMethodField()
    operateurs = serializers.CharField(allow_null=True)
    partenaires = serializers.CharField(allow_null=True)
    sites = serializers.SerializerMethodField()
    # Cadre de l'action : ce qu'elle sert à suivre (#634). Sans lui, la fiche
    # action se réduit à un libellé et une période, et le lien avec
    # l'arborescence — la raison d'être de l'action — reste invisible.
    #: Rattachement à l'arborescence : permet d'afficher l'action **sous**
    #: l'indicateur qu'elle sert, et pas seulement dans une liste à plat.
    id_indicateur = serializers.IntegerField(
        source='id_indicateur_id', allow_null=True)
    indicateur = serializers.SerializerMethodField()
    metriques = serializers.SerializerMethodField()
    #: Indicateurs de réponse liés à l'action, avec leurs métriques et leur
    #: grille : ce qui permet de juger si l'action a produit son effet.
    indicateurs_reponse = serializers.SerializerMethodField()
    suivi = serializers.SerializerMethodField()

    def get_indicateur(self, operation):
        """
        Indicateur(s) d'état ou de pression servi(s) par l'action (#626).

        Une action rejoint l'arborescence par son lien direct **ou** par ses
        métriques : ne lire que le lien direct laissait le cadre vide sur toutes
        les actions rattachées par leurs métriques, qui sont le cas courant.
        """
        from apps.plans.services_export_fiche_action import (
            _is_reponse, _linked_indicateurs,
        )

        noms = []
        for indicateur in _linked_indicateurs(operation):
            if not _is_reponse(indicateur) and indicateur.nom_indicateur not in noms:
                noms.append(indicateur.nom_indicateur)
        return ' ; '.join(noms) or None

    def get_metriques(self, operation):
        from apps.plans.services_export_fiche_action import _is_reponse

        return [
            {'id_metrique': metrique.pk,
             'nom_metrique': metrique.nom_metrique,
             'unite': metrique.unite or None}
            for metrique in operation.metriques.all()
            if not _is_reponse(metrique.id_indicateur)
        ]

    def get_indicateurs_reponse(self, operation):
        """
        Source de vérité partagée avec l'export : `_reponse_indicateurs` (#626).

        Deux implémentations de « quels indicateurs de réponse pour cette
        action » divergeraient, et la fiche publique se mettrait à raconter
        autre chose que le classeur exporté.
        """
        from apps.plans.services_export_fiche_action import _reponse_indicateurs

        return IndicateurPublicSerializer(
            _reponse_indicateurs(operation), many=True).data

    def get_suivi(self, operation):
        suivi = operation.id_suivi
        return SuiviPublicSerializer(suivi).data if suivi else None

    def get_sites(self, operation):
        """Localisation de l'action : les sites qu'elle couvre (#626)."""
        return [
            {'id_site': site.id_site, 'nom_site': site.nom_site,
             'slug': site.slug}
            for site in operation.sites.all()
        ]

    def get_frequence(self, operation):
        if not operation.frequence_nombre and not operation.frequence_unite:
            return None
        unite = _texte(operation.frequence_unite)
        if operation.frequence_nombre and unite:
            return f"{operation.frequence_nombre} / {unite}"
        return unite or str(operation.frequence_nombre)

    def get_categorie(self, operation):
        categorie = operation.id_categorie_action_reserve
        if not categorie:
            return None
        return f"{categorie.mnemonique} - {categorie.label}"

    def get_type_action(self, operation):
        return _label(operation.id_type_action)

    def get_priorite(self, operation):
        return _label(operation.id_priorite)


class NiveauExigencePublicSerializer(serializers.Serializer):
    id_ne = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    indicateurs = IndicateurPublicSerializer(many=True, source='indicateurs_pub')


class ObjectifLongTermePublicSerializer(serializers.Serializer):
    id_olt = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    niveaux_exigence = NiveauExigencePublicSerializer(many=True, source='niveaux_pub')


class ResultatAttenduPublicSerializer(serializers.Serializer):
    id_ra = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    indicateurs = IndicateurPublicSerializer(many=True, source='indicateurs_pub')


class ObjectifOperationnelPublicSerializer(serializers.Serializer):
    id_oo = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    resultats_attendus = ResultatAttenduPublicSerializer(many=True, source='resultats_pub')


class PressionPubliqueSerializer(serializers.Serializer):
    id_pression = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    type_pression = serializers.SerializerMethodField()

    def get_type_pression(self, pression):
        return _label(pression.id_type_pression)


class FacteurInfluencePublicSerializer(serializers.Serializer):
    id_facteur_influence = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    pressions = PressionPubliqueSerializer(many=True, source='pressions_pub')


class EnjeuPublicSerializer(serializers.Serializer):
    id_enjeu = serializers.IntegerField()
    libelle = serializers.CharField()
    intitule_court = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    etat_enjeu = serializers.CharField(allow_null=True)
    rang = serializers.IntegerField(allow_null=True)
    categorie = serializers.SerializerMethodField()
    categorie_ecologique = serializers.BooleanField(allow_null=True)
    taxons = serializers.SerializerMethodField()
    habitats = serializers.SerializerMethodField()
    facteurs = FacteurInfluencePublicSerializer(many=True, source='facteurs_pub')
    objectifs_long_terme = ObjectifLongTermePublicSerializer(many=True, source='olt_pub')
    objectifs_operationnels = ObjectifOperationnelPublicSerializer(many=True, source='oo_pub')

    def get_categorie(self, enjeu):
        return _label(enjeu.id_categorie)

    def get_taxons(self, enjeu):
        return [
            {'cd_nom': taxon.cd_nom, 'nom_complet': taxon.nom_complet,
             'nom_vern': taxon.nom_vern}
            for taxon in enjeu.taxons.all()
        ]

    def get_habitats(self, enjeu):
        return [
            {'cd_hab': habitat.cd_hab, 'lb_hab_fr': habitat.lb_hab_fr}
            for habitat in enjeu.habitats.all()
        ]


class FichePubliqueSerializer(serializers.Serializer):
    """Un plan de gestion et sa structure, en lecture seule."""

    id_pg = serializers.IntegerField()
    nom = serializers.CharField()
    slug = serializers.CharField()
    statut = serializers.CharField()
    rang = serializers.IntegerField()
    annee_debut = serializers.IntegerField(allow_null=True)
    annee_fin = serializers.IntegerField(allow_null=True)
    surface = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True,
    )
    type_document = serializers.SerializerMethodField()
    sites = serializers.SerializerMethodField()
    gestionnaire_principal = serializers.SerializerMethodField()
    enjeux = EnjeuPublicSerializer(many=True, source='enjeux_pub')
    actions = ActionPubliqueSerializer(many=True, source='actions_pub')

    def get_type_document(self, plan):
        return _label(plan.id_type_document)

    def get_sites(self, plan):
        return [
            {
                'id_site': lien.site.id_site,
                'nom_site': lien.site.nom_site,
                'slug': lien.site.slug,
                'type_site': (
                    lien.site.id_type_site.mnemonique
                    if lien.site.id_type_site_id else None
                ),
            }
            for lien in plan.sites_ordonnes
        ]

    def get_gestionnaire_principal(self, plan):
        for lien in plan.sites_ordonnes:
            gestionnaires = getattr(lien.site, 'gestionnaires_principaux', [])
            if gestionnaires:
                return gestionnaires[0].uuid_og.nom_organisme
        return None
