"""
#560 — Données initiales RH.

1. Seed du socle global de fonctions/postes (idempotent).
2. Conversion du « Travail prévisionnel (jours) » existant (OperationAnnee.etp,
   éventuellement ventilé par organisme) en une ligne RH « financé, fonction non
   précisée ».
3. Idem pour le réalisé (RealisationOperationAnnee.etp_realise).

Les colonnes etp / etp_realise sont conservées (dépréciées) : cette migration ne
les supprime pas, la conversion est donc non destructive et réversible.
"""
from decimal import Decimal

from django.db import migrations


# Socle de fonctions : (libellé, financé par défaut)
SOCLE_FONCTIONS = [
    ("Conservateur", True),
    ("Garde", True),
    ("Garde-technicien", True),
    ("Animateur nature", True),
    ("Responsable scientifique", True),
    ("Chargé de mission", True),
    ("Chargé d'études", True),
    ("Chargé de communication", True),
    ("Technicien", True),
    ("Directeur", True),
    ("Stagiaire", True),
    ("Alternant / apprenti", True),
    ("Service civique", True),
    ("Prestataire", True),
    ("Écovolontaire", False),
    ("Bénévole", False),
    ("Partenaire", False),
]


def _sum_decimal(values):
    total = None
    for v in values:
        if v is None:
            continue
        total = (total or Decimal("0")) + v
    return total


def seed_and_migrate(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    OperationAnnee = apps.get_model("plans", "OperationAnnee")
    OperationAnneeRH = apps.get_model("plans", "OperationAnneeRH")
    RealisationOperationAnnee = apps.get_model("plans", "RealisationOperationAnnee")
    RealisationOperationAnneeRH = apps.get_model("plans", "RealisationOperationAnneeRH")

    # 1. Socle de fonctions
    for libelle, finance in SOCLE_FONCTIONS:
        Fonction.objects.update_or_create(
            libelle=libelle,
            defaults={"finance_par_defaut": finance, "is_socle": True, "actif": True},
        )

    # 2. Prévisionnel : etp -> ligne RH
    for oa in OperationAnnee.objects.all().prefetch_related("organismes"):
        if OperationAnneeRH.objects.filter(id_operation_annee=oa).exists():
            continue
        effective = oa.etp
        if effective is None:
            effective = _sum_decimal(org.etp for org in oa.organismes.all())
        if effective is None or effective == 0:
            continue
        OperationAnneeRH.objects.create(
            id_operation_annee=oa,
            id_personne_plan=None,
            id_fonction=None,
            jours=effective,
            finance=True,
        )

    # 3. Réalisé : etp_realise -> ligne RH
    reals = RealisationOperationAnnee.objects.all().prefetch_related(
        "id_operation_annee__organismes__realisation"
    )
    for real in reals:
        if RealisationOperationAnneeRH.objects.filter(
            id_realisation_operation_annee=real
        ).exists():
            continue
        effective = real.etp_realise
        if effective is None:
            oa = real.id_operation_annee
            effective = _sum_decimal(
                getattr(getattr(org, "realisation", None), "etp_realise", None)
                for org in oa.organismes.all()
            )
        if effective is None or effective == 0:
            continue
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=real,
            id_personne_plan=None,
            id_fonction=None,
            jours=effective,
            finance=True,
        )


def reverse(apps, schema_editor):
    # Supprime les lignes RH migrées (fonction/personne non précisées) et le socle.
    Fonction = apps.get_model("plans", "Fonction")
    OperationAnneeRH = apps.get_model("plans", "OperationAnneeRH")
    RealisationOperationAnneeRH = apps.get_model("plans", "RealisationOperationAnneeRH")

    OperationAnneeRH.objects.filter(
        id_personne_plan__isnull=True, id_fonction__isnull=True
    ).delete()
    RealisationOperationAnneeRH.objects.filter(
        id_personne_plan__isnull=True, id_fonction__isnull=True
    ).delete()
    Fonction.objects.filter(is_socle=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0099_fonction_personneplan_operationanneerh_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_and_migrate, reverse),
    ]
