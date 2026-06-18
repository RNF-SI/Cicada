"""
#379 — Ajoute le niveau de réalisation « Non réalisée » (NON_REALISE) au
type NIVEAU_REALISATION. Idempotent : ne fait rien si déjà présent.
"""
from django.db import migrations


def add_non_realise(apps, schema_editor):
    Nomenclature = apps.get_model('core', 'Nomenclature')
    TypeNomenclature = apps.get_model('core', 'TypeNomenclature')
    try:
        type_obj = TypeNomenclature.objects.get(mnemonique='NIVEAU_REALISATION')
    except TypeNomenclature.DoesNotExist:
        # Le type sera créé par l'import des nomenclatures (qui inclut déjà NON_REALISE).
        return
    Nomenclature.objects.get_or_create(
        id_type=type_obj,
        mnemonique='NON_REALISE',
        defaults={
            'cd_nomenclature': 'NON_REALISE',
            'label': 'Non réalisée',
            'definition': 'Action prévue mais non réalisée pour cette année',
            'source': 'CICADA',
            'statut': 'Validé',
            'hierarchy': '7',
            'actif': True,
        },
    )


def remove_non_realise(apps, schema_editor):
    Nomenclature = apps.get_model('core', 'Nomenclature')
    Nomenclature.objects.filter(
        id_type__mnemonique='NIVEAU_REALISATION', mnemonique='NON_REALISE'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_add_homepage_image_position'),
    ]

    operations = [
        migrations.RunPython(add_non_realise, remove_non_realise),
    ]
