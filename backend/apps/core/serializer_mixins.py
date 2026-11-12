"""Garde-fous communs aux serializers d'écriture."""
from rest_framework.fields import empty


class SansValeurParDefautEnMiseAJourMixin:
    """Un champ absent d'une mise à jour garde sa valeur, même en ``PUT``.

    DRF applique la valeur par défaut d'un champ absent dès que la requête
    n'est pas partielle : un ``PUT`` (client tiers, Swagger) qui omet une liste
    imbriquée déclarée ``default=[]`` (programmation, financements, taxons…)
    la remettait donc à vide, et la mise à jour « tout remplacer » effaçait
    l'existant. À la création, la valeur par défaut reste appliquée.
    """

    def to_internal_value(self, data):
        valeurs = super().to_internal_value(data)
        if self.instance is None or not hasattr(data, 'keys'):
            return valeurs
        for nom, champ in self.fields.items():
            if champ.read_only or nom in data or champ.default is empty:
                continue
            source = champ.source
            if source and source != '*' and source in valeurs:
                valeurs.pop(source)
        return valeurs
