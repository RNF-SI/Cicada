"""
Restructuration ObjectifOperationnel – étape 1 : migration de données.

Pour les OO sans facteur_influence, crée un FacteurInfluence par défaut.
"""
from django.db import migrations


def migrate_data_forward(apps, schema_editor):
    """
    Pour chaque OO sans facteur_influence :
    - Créer un FacteurInfluence sous son enjeu
    - Rattacher l'OO à ce FacteurInfluence
    """
    ObjectifOperationnel = apps.get_model('plans', 'ObjectifOperationnel')
    FacteurInfluence = apps.get_model('plans', 'FacteurInfluence')

    for oo in ObjectifOperationnel.objects.filter(id_facteur_influence__isnull=True):
        fi = FacteurInfluence.objects.create(
            id_enjeu_id=oo.id_enjeu_id,
            libelle=f"Facteur d'influence de {oo.libelle}",
            description="",
            id_utilisateur_ajout_id=oo.id_utilisateur_ajout_id,
            id_utilisateur_maj_id=oo.id_utilisateur_maj_id,
        )
        oo.id_facteur_influence = fi
        oo.save(update_fields=['id_facteur_influence_id'])


def migrate_data_backward(apps, schema_editor):
    """No-op: backward handled by migration 0031."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0029_restructure_etat_actuel_olt'),
    ]

    operations = [
        migrations.RunPython(migrate_data_forward, migrate_data_backward),
    ]
