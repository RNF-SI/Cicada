"""
#631 — Une fonction ajoutée à la volée reste à l'échelle de son plan.

Le référentiel était entièrement partagé : compléter sa liste de fonctions
depuis un plan la faisait apparaître chez tout le monde. On ajoute donc une
portée (`id_pg`) : vide = socle partagé, renseigné = propre à ce plan.

Les fonctions déjà créées par les gestionnaires sont rattachées au plan qui les
utilise, quand il n'y en a qu'un. Utilisées par plusieurs plans (ou par aucun
poste), elles restent partagées : on ne devine pas à qui elles appartiennent, et
les retirer casserait des postes existants.
"""

import django.db.models.deletion
from django.db import migrations, models


# Contrainte UNIQUE portant sur le seul `libelle`, quel que soit le nom qu'elle
# porte selon l'historique de la base.
UNIQUE_LIBELLE_SEUL = """
    SELECT con.conname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = rel.relnamespace
    WHERE ns.nspname = 'general'
      AND rel.relname = 't_fonctions'
      AND con.contype = 'u'
      AND con.conkey = ARRAY[(
          SELECT attnum FROM pg_attribute
          WHERE attrelid = rel.oid AND attname = 'libelle'
      )]
"""


def supprimer_unique_libelle(apps, schema_editor):
    """
    `db_table` étant qualifié et cité ('"general"."t_fonctions"'), Django ne
    retrouve pas la table à l'introspection : retirer `unique=True` du modèle ne
    supprime pas la contrainte, qui interdirait à deux plans de nommer leur
    fonction pareil. On la retire donc à la main, sans présumer de son nom — et
    toutes celles qui traînent, un aller-retour de migration pouvant en laisser
    plusieurs (`t_fonctions_libelle_key` d'origine + celle recréée par Django).

    Le retour arrière n'a rien à faire : c'est l'`AlterField` inverse qui
    recrée la contrainte d'unicité globale.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(UNIQUE_LIBELLE_SEUL)
        for (nom,) in cursor.fetchall():
            cursor.execute(f'ALTER TABLE general.t_fonctions DROP CONSTRAINT "{nom}"')


def rattacher_fonctions_aux_plans(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    PosteFonction = apps.get_model("plans", "PosteFonction")

    for fonction in Fonction.objects.filter(is_socle=False, id_pg__isnull=True):
        plan_ids = set(
            PosteFonction.objects.filter(id_fonction=fonction).values_list(
                "id_poste__id_pg", flat=True
            )
        )
        plan_ids.discard(None)
        if len(plan_ids) == 1:
            fonction.id_pg_id = plan_ids.pop()
            fonction.save(update_fields=["id_pg"])


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0119_retire_fonction_prestataire"),
    ]

    operations = [
        migrations.AlterModelTableComment(
            name="fonction",
            table_comment="Fonctions/postes : socle global (id_pg NULL) + fonctions propres à un plan de gestion (#560, #631)",
        ),
        migrations.AddField(
            model_name="fonction",
            name="id_pg",
            field=models.ForeignKey(
                blank=True,
                db_column="id_pg",
                help_text="Plan auquel la fonction est propre (#631). Vide pour une fonction du socle, partagée par tous les plans.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fonctions",
                to="plans.plangestion",
                verbose_name="Plan de gestion",
            ),
        ),
        migrations.AlterField(
            model_name="fonction",
            name="libelle",
            field=models.CharField(max_length=150, verbose_name="Libellé"),
        ),
        migrations.RunPython(supprimer_unique_libelle, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="fonction",
            constraint=models.UniqueConstraint(
                condition=models.Q(("id_pg__isnull", True)),
                fields=("libelle",),
                name="uniq_fonction_socle_libelle",
            ),
        ),
        migrations.AddConstraint(
            model_name="fonction",
            constraint=models.UniqueConstraint(
                fields=("libelle", "id_pg"), name="uniq_fonction_plan_libelle"
            ),
        ),
        # Reverse : la colonne id_pg est supprimée juste après, rien à défaire.
        migrations.RunPython(
            rattacher_fonctions_aux_plans, migrations.RunPython.noop
        ),
    ]
