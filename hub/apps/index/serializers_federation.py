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
from .models import VALIDATEUR_IDENTIFIANT, ContenuIndexe

#: Empreinte SHA-256 d'un jeton, telle que ``Instance.empreinte`` la produit :
#: 64 caractères hexadécimaux **minuscules**. Une majuscule ne correspondrait
#: jamais à l'empreinte calculée à l'authentification.
EMPREINTE = r'^[0-9a-f]{64}$'
MESSAGE_EMPREINTE = (
    "Empreinte attendue : SHA-256 en 64 caractères hexadécimaux minuscules."
)


class OuvertureLotSerializer(serializers.Serializer):
    """
    Corps de l'ouverture d'un lot.

    L'instance y **déclare son identité d'affichage** : le nom qu'elle se donne
    et son URL publique. Ils ne l'authentifient pas — c'est le jeton qui le
    fait, et l'identifiant technique en est déduit — ils servent à nommer la
    provenance d'un résultat dans l'interface. Facultatifs : une instance plus
    ancienne n'en envoie pas, et le hub retombe alors sur le registre.
    """

    format_version = serializers.IntegerField()
    libelle = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default='',
    )
    url_publique = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default='',
    )

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
    # #681/#682 — optionnels : une instance antérieure ne les envoie pas.
    enfants = serializers.CharField(allow_blank=True, required=False, default='')
    chemin = serializers.ListField(
        child=serializers.DictField(), required=False, default=list,
    )
    enjeu_slug = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True,
    )

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
    # #676 — optionnel : une instance antérieure à ce champ ne l'envoie pas.
    annees_extension = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=2, default=0,
    )
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
    # #683 — même statut que la fiche : un instantané rendu par l'instance,
    # stocké et resservi sans être inspecté. Optionnel : une instance
    # antérieure ne l'envoie pas.
    ecrans = serializers.DictField(required=False)

    contenus = ContenuSerializer(many=True, required=False)


class PagePlansSerializer(serializers.Serializer):
    """Une page de plans déposée dans un lot ouvert."""

    plans = PlanPublieSerializer(many=True, allow_empty=True)


class EnrolementSerializer(serializers.Serializer):
    """
    Corps d'un enrôlement délégué à l'API de suivi RNF (#696).

    L'instance a tiré **elle-même** ses deux jetons et n'en a transmis que les
    empreintes : le hub les range telles quelles, sans jamais voir un jeton. La
    validation est donc stricte sur leur forme — une empreinte mal formée
    produirait une instance enrôlée que rien ne pourrait jamais authentifier,
    échec silencieux qu'il vaut mieux refuser à l'entrée.

    L'identifiant suit la même règle que ``enroler_instance`` : il est repris
    dans chaque ligne d'index et dans la référence publique des plans.
    """

    instance_id = serializers.CharField(
        max_length=64, validators=[VALIDATEUR_IDENTIFIANT],
    )
    libelle = serializers.CharField(max_length=200)
    url_publique = serializers.URLField(
        max_length=200, required=False, allow_blank=True, default='',
    )
    empreinte_depot = serializers.RegexField(
        EMPREINTE, error_messages={'invalid': MESSAGE_EMPREINTE},
    )
    empreinte_lecture = serializers.RegexField(
        EMPREINTE, error_messages={'invalid': MESSAGE_EMPREINTE},
    )

    def validate(self, donnees):
        # Une même empreinte pour les deux usages ferait du jeton de lecture un
        # jeton de dépôt : lire et écrire sont deux droits distincts (#636).
        if donnees['empreinte_depot'] == donnees['empreinte_lecture']:
            raise serializers.ValidationError(
                "Les empreintes de dépôt et de lecture doivent être distinctes."
            )
        return donnees
