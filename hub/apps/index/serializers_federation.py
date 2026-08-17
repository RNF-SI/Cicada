"""
Validation du contrat de dépôt.

La validation est **volontairement lâche sur les champs d'affichage** et stricte
sur ce qui structure l'index. Un libellé absent produit une tuile un peu vide ;
un `id_pg` absent produit un plan que rien ne permettra jamais de retrouver ni
de remplacer. Les deux ne méritent pas le même traitement.

Les instances étant mises à jour indépendamment, un émetteur peut envoyer des
champs que ce hub ne connaît pas encore : ils sont ignorés, pas refusés.
"""

from rest_framework import serializers

from .federation import FORMATS_ACCEPTES
from .models import ContenuIndexe


class OuvertureLotSerializer(serializers.Serializer):
    """Corps de l'ouverture d'un lot."""

    format_version = serializers.IntegerField()

    def validate_format_version(self, valeur):
        if valeur not in FORMATS_ACCEPTES:
            raise serializers.ValidationError(
                f"Format de dépôt {valeur} non pris en charge par ce hub "
                f"(versions acceptées : {sorted(FORMATS_ACCEPTES)}). "
                f"L'instance est-elle plus récente que le hub ?"
            )
        return valeur


class ContenuSerializer(serializers.Serializer):
    """Un objet explorable d'un plan."""

    type_contenu = serializers.ChoiceField(
        choices=[code for code, _ in ContenuIndexe.TYPE_CHOICES]
    )
    id_objet = serializers.IntegerField()
    titre = serializers.CharField(max_length=500, allow_blank=True)

    description = serializers.CharField(
        allow_blank=True, required=False, default=''
    )
    rattachements = serializers.CharField(
        allow_blank=True, required=False, default=''
    )
    contexte = serializers.CharField(allow_blank=True, required=False, default='')

    parent_type = serializers.CharField(
        max_length=20, required=False, allow_null=True, allow_blank=True
    )
    parent_libelle = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )
    sous_type = serializers.CharField(
        max_length=50, required=False, allow_null=True, allow_blank=True
    )
    sous_type_libelle = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    index_version = serializers.IntegerField(required=False, default=0)


class PlanPublieSerializer(serializers.Serializer):
    """Un plan publié, avec son contenu et sa fiche."""

    id_pg = serializers.IntegerField()
    nom = serializers.CharField(max_length=500)
    statut = serializers.CharField(max_length=20)

    slug = serializers.CharField(max_length=255, required=False, allow_blank=True)
    url_instance = serializers.CharField(required=False, allow_blank=True)
    rang = serializers.IntegerField(required=False, allow_null=True)
    annee_debut = serializers.IntegerField(required=False, allow_null=True)
    annee_fin = serializers.IntegerField(required=False, allow_null=True)
    type_document = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    gestionnaire_principal = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )

    sites = serializers.ListField(child=serializers.DictField(), required=False)
    site_inpn_codes = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False
    )
    type_site_codes = serializers.ListField(
        child=serializers.CharField(max_length=25), required=False
    )
    area_codes = serializers.ListField(
        child=serializers.CharField(max_length=60), required=False,
        help_text="Codes nationaux préfixés par le type : « DEP:13 », « REG:93 ».",
    )

    # La fiche n'est pas validée dans le détail : c'est un arbre rendu par les
    # sérialiseurs de l'instance, que le hub stocke et ressert sans l'inspecter.
    # La valider ici reviendrait à recopier le schéma de la fiche de CICADA, et
    # donc à devoir le suivre à chaque évolution — exactement ce que
    # l'instantané JSON permet d'éviter.
    fiche = serializers.DictField(required=False)

    contenus = ContenuSerializer(many=True, required=False)


class PagePlansSerializer(serializers.Serializer):
    """Une page de plans déposée dans un lot ouvert."""

    plans = PlanPublieSerializer(many=True, allow_empty=True)
