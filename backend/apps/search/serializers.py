"""
Sérialiseurs de l'exploration des données.

Les tuiles de résultat affichent le plan, ses sites, son gestionnaire principal
et sa période. Ces libellés ne sont **pas** dénormalisés dans l'index : ils sont
joints à la volée, une page ne contenant qu'une vingtaine de résultats. Une
donnée jointe ne peut pas devenir obsolète, contrairement à une copie.
"""

from django.db.models import Prefetch
from rest_framework import serializers

from apps.plans.models import CorSitePg, PlanGestion
from apps.users.models import CorOgSite

from .filters import CHAMPS_CORRESPONDANCE, CHAMPS_EXTRAITS
from .models import ContenuIndexe
from .surlignage import extrait_autour, mots_proches


def prefetch_sites():
    """
    Prefetch des sites d'un plan, avec leur gestionnaire principal.

    Sans ça, chaque tuile déclencherait une requête par site puis une par
    organisme — soit une cinquantaine de requêtes pour une page de résultats.

    Vit ici plutôt que dans les vues parce que la publication vers le hub
    (`push.py`) en a le même besoin : c'est ce prefetch qui alimente
    `_sites_du_plan`, et l'oublier ne casse rien visiblement — la liste des
    sites ressort simplement vide.
    """
    gestionnaires = Prefetch(
        'site__corogsite_set',
        queryset=CorOgSite.objects.filter(principal=True).select_related('uuid_og'),
        to_attr='gestionnaires_principaux',
    )
    return Prefetch(
        'sites',
        queryset=(
            CorSitePg.objects
            .select_related('site')
            .prefetch_related(gestionnaires)
            .order_by('rang', 'site__nom_site')
        ),
        to_attr='sites_ordonnes',
    )


def _gestionnaire_principal(site):
    """Nom de l'organisme gestionnaire principal d'un site, si prefetché."""
    liens = getattr(site, 'gestionnaires_principaux', None)
    if not liens:
        return None
    return liens[0].uuid_og.nom_organisme


def _sites_du_plan(plan):
    """Sites du plan, du principal (rang 1) au dernier."""
    return [lien.site for lien in getattr(plan, 'sites_ordonnes', [])]


class SiteResumeSerializer(serializers.Serializer):
    """Site tel qu'affiché sur une tuile de résultat."""

    id_site = serializers.IntegerField()
    nom_site = serializers.CharField()
    slug = serializers.CharField()


class PlanResumeSerializer(serializers.Serializer):
    """Bandeau « Plan de gestion / Gestionnaire / Période » d'une tuile."""

    id_pg = serializers.IntegerField()
    nom = serializers.CharField()
    slug = serializers.CharField()
    statut = serializers.CharField()
    annee_debut = serializers.IntegerField(allow_null=True)
    annee_fin = serializers.IntegerField(allow_null=True)
    type_document = serializers.SerializerMethodField()
    sites = serializers.SerializerMethodField()
    gestionnaire_principal = serializers.SerializerMethodField()

    def get_type_document(self, plan):
        return plan.id_type_document.label if plan.id_type_document_id else None

    def get_sites(self, plan):
        return SiteResumeSerializer(_sites_du_plan(plan), many=True).data

    def get_gestionnaire_principal(self, plan):
        # Le gestionnaire affiché est celui du site principal du plan.
        for site in _sites_du_plan(plan):
            nom = _gestionnaire_principal(site)
            if nom:
                return nom
        return None


class ContenuResultatSerializer(serializers.ModelSerializer):
    """Une tuile de résultat du mode « contenu d'un plan de gestion »."""

    plan = serializers.SerializerMethodField()

    correspondances = serializers.SerializerMethodField()
    extraits = serializers.SerializerMethodField()
    termes_surlignes = serializers.SerializerMethodField()
    acces_direct = serializers.SerializerMethodField()

    class Meta:
        model = ContenuIndexe
        fields = [
            'id', 'type_contenu', 'id_objet',
            'titre', 'description',
            'parent_type', 'parent_libelle',
            # #682 — l'arborescence qui mène à l'objet, et la branche à ouvrir.
            'chemin', 'enjeu_slug',
            'sous_type', 'sous_type_libelle',
            'instance_id',
            # #650 / #681 — pourquoi ce résultat est là, et quel mot surligner.
            'correspondances', 'extraits', 'termes_surlignes',
            # #683 — ce plan existe dans cette base : ses écrans réels s'ouvrent.
            'acces_direct', 'plan',
        ]

    def get_acces_direct(self, contenu):
        """
        Vrai si l'objet peut s'ouvrir dans les écrans réels du plan (#683).

        C'est le cas de tout document produit ici : le plan est validé (sinon
        il ne serait pas indexé) et sa structure est lisible par tout
        utilisateur connecté (cf. `apps.plans.exploration`). Un document reçu
        d'une autre instance n'a pas de plan dans cette base : seule sa fiche
        publique — l'instantané déposé — peut être montrée.
        """
        return contenu.id_pg_id is not None

    def get_plan(self, contenu):
        """
        Bandeau du plan — joint pour un document local, recopié pour un distant.

        Un document reçu d'une autre instance (#636) n'a pas de plan dans cette
        base : `id_pg` est NULL et l'affichage vient du snapshot capturé à la
        publication. Les deux chemins produisent la même forme, pour que
        l'interface n'ait pas à distinguer les deux cas.
        """
        if contenu.id_pg_id is None:
            return contenu.plan_denorm or None
        return PlanResumeSerializer(contenu.id_pg).data


    def get_correspondances(self, contenu):
        """
        Champs ayant répondu à la recherche (#650).

        Vide quand la requête ne porte pas de mot-clé : il n'y a alors rien à
        expliquer. Les objets rattachés — espèces, habitats, protocoles — sont
        interrogés mais jamais affichés sur la tuile : sans cette liste, un
        résultat dont le titre n'a aucun rapport visible avec la requête paraît
        arbitraire alors qu'il est pertinent.
        """
        return [
            champ for champ in CHAMPS_CORRESPONDANCE
            if getattr(contenu, f'correspond_{champ}', False)
        ]

    def _approximatif(self):
        return bool(self.context.get('approximatif'))

    def _mot_cle(self):
        return (self.context.get('mot_cle') or '').strip()

    def get_termes_surlignes(self, contenu):
        """
        Mots à surligner sur la tuile quand ils diffèrent de la requête (#681).

        En recherche exacte, l'interface surligne les mots tapés et la
        radicalisation fait le reste. En repli approximatif, le mot retenu
        n'est pas celui qui a été tapé : on le désigne explicitement, sinon
        le résultat n'a aucun mot surligné et se lit comme une erreur.
        """
        if not self._approximatif():
            return []
        textes = [contenu.titre, contenu.rattachements, contenu.enfants] + [
            maillon.get('libelle', '') for maillon in (contenu.chemin or [])
        ]
        return mots_proches(' '.join(t for t in textes if t), self._mot_cle())

    def get_extraits(self, contenu):
        """
        Passage qui a répondu, par champ, sans balisage (#650, #681).

        Ces champs sont des blocs de texte sans séparateur : seul `ts_headline`
        sait y isoler le passage utile — et, en repli approximatif, une fenêtre
        autour du mot le plus proche en tient lieu. Le surlignage est laissé à
        l'interface, pour ne pas faire transiter du HTML depuis la base.
        """
        extraits = {}
        for champ in CHAMPS_EXTRAITS:
            if not getattr(contenu, f'correspond_{champ}', False):
                continue
            if self._approximatif():
                texte = getattr(contenu, champ, '') or ''
                extrait = extrait_autour(texte, mots_proches(texte, self._mot_cle()))
            else:
                extrait = getattr(contenu, f'extrait_{champ}', None)
            if extrait:
                extraits[champ] = extrait
        return extraits


class PlanResultatSerializer(serializers.ModelSerializer):
    """Une tuile de résultat du mode « plan de gestion »."""

    type_document = serializers.SerializerMethodField()
    sites = serializers.SerializerMethodField()
    gestionnaire_principal = serializers.SerializerMethodField()
    # #683 — un plan de cette base s'ouvre dans ses écrans réels.
    acces_direct = serializers.ReadOnlyField(default=True)

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'statut', 'rang',
            'annee_debut', 'annee_fin',
            'type_document', 'sites', 'gestionnaire_principal',
            'acces_direct',
        ]

    def get_type_document(self, plan):
        return plan.id_type_document.label if plan.id_type_document_id else None

    def get_sites(self, plan):
        return SiteResumeSerializer(_sites_du_plan(plan), many=True).data

    def get_gestionnaire_principal(self, plan):
        for site in _sites_du_plan(plan):
            nom = _gestionnaire_principal(site)
            if nom:
                return nom
        return None
