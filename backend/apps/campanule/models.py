"""
Modèles pour le référentiel CAMPanule (INPN).

CAMPanule = CATalogue des Méthodes et des Protocoles de collecte
de données naturalistes.

Schema PostgreSQL : ref_campanule
Source : https://inpn.mnhn.fr/programme/campanule
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


# ============================================================
# Tables principales
# ============================================================

class CampanuleProtocole(models.Model):
    """Protocoles de collecte de données naturalistes."""

    cd_protocole = models.IntegerField(
        _("Code protocole"), primary_key=True
    )
    lb_protocole_court = models.CharField(
        _("Libellé court"), max_length=500, null=True, blank=True
    )
    cd_prot_metier = models.CharField(
        _("Code métier"), max_length=50, null=True, blank=True
    )
    code_v0_9 = models.IntegerField(
        _("Code v0.9"), null=True, blank=True
    )
    cd_prot_ref = models.IntegerField(
        _("Code protocole de référence"), null=True, blank=True,
        db_index=True
    )
    lb_protocole_complet = models.TextField(
        _("Libellé complet"), null=True, blank=True
    )
    lb_protocole_en = models.CharField(
        _("Libellé anglais"), max_length=500, null=True, blank=True
    )
    date_publi = models.CharField(
        _("Date de publication"), max_length=50, null=True, blank=True
    )
    version = models.CharField(
        _("Version"), max_length=100, null=True, blank=True
    )
    obsolete = models.CharField(
        _("Obsolète"), max_length=10, null=True, blank=True
    )
    prot_auteur = models.TextField(
        _("Auteur(s)"), null=True, blank=True
    )
    url_perm = models.TextField(
        _("URL permanente"), null=True, blank=True
    )
    url = models.TextField(
        _("URL"), null=True, blank=True
    )
    url_complementaire = models.TextField(
        _("URL complémentaire"), null=True, blank=True
    )
    description = models.TextField(
        _("Description"), null=True, blank=True
    )
    descr_cible_prot = models.TextField(
        _("Description cible"), null=True, blank=True
    )
    descr_objectif_prot = models.TextField(
        _("Description objectif"), null=True, blank=True
    )
    cible = models.CharField(
        _("Cible principale"), max_length=255, null=True, blank=True,
        db_index=True
    )
    echelle_restit = models.CharField(
        _("Échelle de restitution"), max_length=100, null=True, blank=True
    )
    saisie = models.TextField(
        _("Interface de saisie"), null=True, blank=True
    )
    biologie = models.TextField(
        _("Paramètres biologiques"), null=True, blank=True
    )
    abiotique = models.TextField(
        _("Paramètres abiotiques"), null=True, blank=True
    )
    nature_donnees = models.TextField(
        _("Nature des données"), null=True, blank=True
    )
    analyse_reference = models.TextField(
        _("Référence d'analyse"), null=True, blank=True
    )
    guide_sinp_donnees = models.TextField(
        _("Guide SINP données"), null=True, blank=True
    )
    norme = models.CharField(
        _("Norme"), max_length=255, null=True, blank=True
    )
    indicateur = models.TextField(
        _("Indicateur"), null=True, blank=True
    )
    categorie_prot = models.CharField(
        _("Catégorie"), max_length=255, null=True, blank=True,
        db_index=True
    )
    uuid = models.CharField(
        _("UUID"), max_length=36, null=True, blank=True, unique=True
    )
    gele = models.CharField(
        _("Gelé"), max_length=10, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."protocoles"'
        managed = True
        verbose_name = _("Protocole CAMPanule")
        verbose_name_plural = _("Protocoles CAMPanule")

    def __str__(self):
        return self.lb_protocole_court or f"P{self.cd_protocole}"


class CampanuleMethode(models.Model):
    """Méthodes de collecte de données."""

    cd_methode = models.IntegerField(
        _("Code méthode"), primary_key=True
    )
    cd_meth_metier = models.CharField(
        _("Code métier"), max_length=50, null=True, blank=True
    )
    lb_methode_court = models.CharField(
        _("Libellé court"), max_length=500, null=True, blank=True
    )
    lb_methode_complet = models.TextField(
        _("Libellé complet"), null=True, blank=True
    )
    lb_methode_en = models.CharField(
        _("Libellé anglais"), max_length=500, null=True, blank=True
    )
    url_perm = models.TextField(
        _("URL permanente"), null=True, blank=True
    )
    url_complementaire = models.TextField(
        _("URL complémentaire"), null=True, blank=True
    )
    descr_methode = models.TextField(
        _("Description"), null=True, blank=True
    )
    exemples_cible_meth = models.TextField(
        _("Exemples de cibles"), null=True, blank=True
    )
    descr_objectif_meth = models.TextField(
        _("Description objectif"), null=True, blank=True
    )
    nature_donnees = models.CharField(
        _("Nature des données"), max_length=500, null=True, blank=True
    )
    analyse_reference = models.TextField(
        _("Référence d'analyse"), null=True, blank=True
    )
    uuid = models.CharField(
        _("UUID"), max_length=36, null=True, blank=True, unique=True
    )
    gele = models.CharField(
        _("Gelé"), max_length=10, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."methodes"'
        managed = True
        verbose_name = _("Méthode CAMPanule")
        verbose_name_plural = _("Méthodes CAMPanule")

    def __str__(self):
        return self.lb_methode_court or f"M{self.cd_methode}"


class CampanuleTechnique(models.Model):
    """Techniques de collecte de données."""

    cd_technique = models.IntegerField(
        _("Code technique"), primary_key=True
    )
    lb_technique_fr = models.CharField(
        _("Libellé français"), max_length=500, null=True, blank=True
    )
    niveau = models.IntegerField(
        _("Niveau hiérarchique"), null=True, blank=True
    )
    cd_tech_metier = models.CharField(
        _("Code métier"), max_length=50, null=True, blank=True
    )
    cd_tech_sup = models.IntegerField(
        _("Code technique supérieure"), null=True, blank=True,
        db_index=True
    )
    lb_tech_complet_fr = models.TextField(
        _("Libellé complet français"), null=True, blank=True
    )
    lb_technique_en = models.CharField(
        _("Libellé anglais"), max_length=500, null=True, blank=True
    )
    categorie_tech = models.CharField(
        _("Catégorie"), max_length=255, null=True, blank=True,
        db_index=True
    )
    cible = models.CharField(
        _("Cible principale"), max_length=255, null=True, blank=True
    )
    descr_technique = models.TextField(
        _("Description"), null=True, blank=True
    )
    descr_cible_tech = models.TextField(
        _("Description cible"), null=True, blank=True
    )
    active = models.CharField(
        _("Active/Passive"), max_length=50, null=True, blank=True
    )
    derangement = models.CharField(
        _("Dérangement"), max_length=100, null=True, blank=True
    )
    prelevement = models.CharField(
        _("Prélèvement"), max_length=100, null=True, blank=True
    )
    comm_collecte = models.TextField(
        _("Commentaire collecte"), null=True, blank=True
    )
    corresp_occtax = models.TextField(
        _("Correspondance OccTax"), null=True, blank=True
    )
    corresp_soh = models.TextField(
        _("Correspondance SOH"), null=True, blank=True
    )
    tag_tax = models.CharField(
        _("Tag taxons"), max_length=10, null=True, blank=True
    )
    tag_hab = models.CharField(
        _("Tag habitats"), max_length=10, null=True, blank=True
    )
    uuid = models.CharField(
        _("UUID"), max_length=36, null=True, blank=True, unique=True
    )
    gele = models.CharField(
        _("Gelé"), max_length=10, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."techniques"'
        managed = True
        verbose_name = _("Technique CAMPanule")
        verbose_name_plural = _("Techniques CAMPanule")

    def __str__(self):
        return self.lb_technique_fr or f"T{self.cd_technique}"


# ============================================================
# Tables complémentaires
# ============================================================

class CampanuleAttribut(models.Model):
    """Attributs (vocabulaire contrôlé) des protocoles et techniques."""

    cd_attribut = models.IntegerField(
        _("Code attribut"), primary_key=True
    )
    lb_attribut = models.CharField(
        _("Libellé"), max_length=500, null=True, blank=True
    )
    categorie_attribut = models.CharField(
        _("Catégorie"), max_length=100, null=True, blank=True,
        db_index=True
    )

    class Meta:
        db_table = '"ref_campanule"."attributs"'
        managed = True
        verbose_name = _("Attribut CAMPanule")
        verbose_name_plural = _("Attributs CAMPanule")

    def __str__(self):
        return self.lb_attribut or f"A{self.cd_attribut}"


class CampanuleProtEchantillonnage(models.Model):
    """Plans d'échantillonnage des protocoles."""

    cd_prot_echantillonnage = models.IntegerField(
        _("Code échantillonnage"), primary_key=True
    )
    cd_protocole = models.IntegerField(
        _("Code protocole"), db_index=True
    )
    unite = models.TextField(
        _("Unité d'échantillonnage"), null=True, blank=True
    )
    nb_unite = models.CharField(
        _("Nombre d'unités"), max_length=255, null=True, blank=True
    )
    duree = models.CharField(
        _("Durée"), max_length=255, null=True, blank=True
    )
    taille = models.CharField(
        _("Taille"), max_length=255, null=True, blank=True
    )
    passages_an = models.CharField(
        _("Passages par an"), max_length=255, null=True, blank=True
    )
    periode_an = models.TextField(
        _("Période de l'année"), null=True, blank=True
    )
    plan_ech = models.CharField(
        _("Plan d'échantillonnage"), max_length=255, null=True, blank=True
    )
    commentaire = models.TextField(
        _("Commentaire"), null=True, blank=True
    )
    niveau = models.CharField(
        _("Niveau d'emboîtement"), max_length=50, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."prot_echantillonnage"'
        managed = True
        verbose_name = _("Échantillonnage protocole")
        verbose_name_plural = _("Échantillonnages protocoles")

    def __str__(self):
        return f"Ech {self.cd_prot_echantillonnage} (P{self.cd_protocole})"


class CampanuleDocsWeb(models.Model):
    """Références bibliographiques (DOCS-Web INPN)."""

    cd_doc = models.IntegerField(
        _("Code document"), primary_key=True
    )
    reference = models.TextField(
        _("Référence bibliographique"), null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."docs_web"'
        managed = True
        verbose_name = _("Document CAMPanule")
        verbose_name_plural = _("Documents CAMPanule")

    def __str__(self):
        ref = self.reference or ""
        return ref[:80] if len(ref) > 80 else ref or f"Doc {self.cd_doc}"


# ============================================================
# Tables de correspondance
# ============================================================

class CampanuleProtAttributsRel(models.Model):
    """Relation protocole-attribut."""

    cd_protocole = models.IntegerField(
        _("Code protocole"), db_index=True
    )
    cd_attribut = models.IntegerField(
        _("Code attribut"), db_index=True
    )

    class Meta:
        db_table = '"ref_campanule"."prot_attributs_rel"'
        managed = True
        unique_together = [('cd_protocole', 'cd_attribut')]
        verbose_name = _("Relation protocole-attribut")
        verbose_name_plural = _("Relations protocole-attribut")


class CampanuleProtBiblioRel(models.Model):
    """Relation protocole-document."""

    cd_protocole = models.IntegerField(
        _("Code protocole"), db_index=True
    )
    cd_doc = models.IntegerField(
        _("Code document"), db_index=True
    )
    page = models.CharField(
        _("Page"), max_length=100, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."prot_biblio_rel"'
        managed = True
        verbose_name = _("Relation protocole-document")
        verbose_name_plural = _("Relations protocole-document")


class CampanuleProtMethRel(models.Model):
    """Relation protocole-méthode."""

    cd_protocole = models.IntegerField(
        _("Code protocole"), db_index=True
    )
    cd_methode = models.IntegerField(
        _("Code méthode"), db_index=True
    )
    commentaire = models.TextField(
        _("Commentaire"), null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."prot_meth_rel"'
        managed = True
        verbose_name = _("Relation protocole-méthode")
        verbose_name_plural = _("Relations protocole-méthode")


class CampanuleProtTechRel(models.Model):
    """Relation protocole-technique."""

    cd_protocole = models.IntegerField(
        _("Code protocole"), db_index=True
    )
    cd_technique = models.IntegerField(
        _("Code technique"), db_index=True
    )
    commentaire = models.TextField(
        _("Commentaire"), null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."prot_tech_rel"'
        managed = True
        verbose_name = _("Relation protocole-technique")
        verbose_name_plural = _("Relations protocole-technique")


class CampanuleMethAttributsRel(models.Model):
    """Relation méthode-attribut."""

    cd_methode = models.IntegerField(
        _("Code méthode"), db_index=True
    )
    cd_attribut = models.IntegerField(
        _("Code attribut"), db_index=True
    )

    class Meta:
        db_table = '"ref_campanule"."meth_attributs_rel"'
        managed = True
        unique_together = [('cd_methode', 'cd_attribut')]
        verbose_name = _("Relation méthode-attribut")
        verbose_name_plural = _("Relations méthode-attribut")


class CampanuleMethBiblioRel(models.Model):
    """Relation méthode-document."""

    cd_methode = models.IntegerField(
        _("Code méthode"), db_index=True
    )
    cd_doc = models.IntegerField(
        _("Code document"), db_index=True
    )
    page = models.CharField(
        _("Page"), max_length=100, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."meth_biblio_rel"'
        managed = True
        verbose_name = _("Relation méthode-document")
        verbose_name_plural = _("Relations méthode-document")


class CampanuleTechAttributsRel(models.Model):
    """Relation technique-attribut."""

    cd_technique = models.IntegerField(
        _("Code technique"), db_index=True
    )
    cd_attribut = models.IntegerField(
        _("Code attribut"), db_index=True
    )

    class Meta:
        db_table = '"ref_campanule"."tech_attributs_rel"'
        managed = True
        unique_together = [('cd_technique', 'cd_attribut')]
        verbose_name = _("Relation technique-attribut")
        verbose_name_plural = _("Relations technique-attribut")


class CampanuleTechBiblioRel(models.Model):
    """Relation technique-document."""

    cd_technique = models.IntegerField(
        _("Code technique"), db_index=True
    )
    cd_doc = models.IntegerField(
        _("Code document"), db_index=True
    )
    page = models.CharField(
        _("Page"), max_length=100, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."tech_biblio_rel"'
        managed = True
        verbose_name = _("Relation technique-document")
        verbose_name_plural = _("Relations technique-document")


# ============================================================
# Table d'autocomplete
# ============================================================

class AutocompleteProtocole(models.Model):
    """
    Table dénormalisée pour l'autocomplete des protocoles.

    Indexée avec pg_trgm pour la recherche floue.
    Générée par la commande import_campanule.
    """

    cd_protocole = models.IntegerField(
        _("Code protocole"), primary_key=True
    )
    search_name = models.TextField(_("Nom de recherche"))
    lb_protocole_court = models.CharField(
        _("Libellé court"), max_length=500, null=True, blank=True
    )
    lb_protocole_complet = models.TextField(
        _("Libellé complet"), null=True, blank=True
    )
    description = models.TextField(
        _("Description"), null=True, blank=True
    )
    cible = models.CharField(
        _("Cible"), max_length=255, null=True, blank=True
    )
    categorie_prot = models.CharField(
        _("Catégorie"), max_length=255, null=True, blank=True
    )
    prot_auteur = models.TextField(
        _("Auteur(s)"), null=True, blank=True
    )
    obsolete = models.CharField(
        _("Obsolète"), max_length=10, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_campanule"."autocomplete_protocole"'
        managed = True
        verbose_name = _("Autocomplete protocole")
        verbose_name_plural = _("Autocomplete protocoles")

    def __str__(self):
        return self.lb_protocole_court or f"P{self.cd_protocole}"
