"""
#633 — Le type de poste d'une fonction RH devient une nomenclature.

`Fonction` reste un modèle métier (attributs propres, ajout à la volée, portée
par plan #631), mais `type_poste` — vocabulaire contrôlé, fini et stable — passe
du `choices` en dur à la nomenclature TYPE_POSTE (type 70), gérée comme les
autres référentiels.

Le contrat de l'API ne change pas : le code court (« salarie », « benevole »…)
reste échangé, via une propriété du modèle qui lit le mnémonique.

Le seed de la nomenclature n'est PAS conditionné à la présence des autres
nomenclatures : les fonctions du socle en dépendent dès la migration, y compris
sur une base de test qui ne passe pas par `import_nomenclatures`.
"""
import django.db.models.deletion
from django.db import migrations, models


TYPE_ID = 70
# (id_nomenclature, mnémonique, label, définition, ordre)
TYPES_POSTE = [
    (1627, 'SALARIE', 'Salarié',
     "Poste salarié de la structure, saisi au coût jour", '1'),
    (1628, 'STAGIAIRE', 'Stagiaire',
     "Stagiaire ou apprenti, saisi au coût jour", '2'),
    (1629, 'PRESTATAIRE', 'Prestataire',
     "Intervenant extérieur au forfait, sans coût jour ni temps de travail programmé", '3'),
    (1630, 'BENEVOLE', 'Bénévole',
     "Bénévole ou écovolontaire, regroupé et valorisé à coût jour nul", '4'),
    (1631, 'PARTENAIRE', 'Partenaire',
     "Structure partenaire, regroupée et saisie hors référentiel d'organismes", '5'),
]


def seed_nomenclature(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ref_nomenclatures.bib_nomenclatures_types
                (id_type, mnemonique, label, definition, source, statut,
                 date_ajout, date_maj)
            VALUES (%s, 'TYPE_POSTE', 'Type de poste',
                    'Catégorie d''une fonction RH : conditionne la saisie du '
                    'coût jour et le regroupement des postes',
                    'CICADA', 'Validé', NOW(), NOW())
            ON CONFLICT (id_type) DO UPDATE SET
                mnemonique = EXCLUDED.mnemonique,
                label = EXCLUDED.label,
                definition = EXCLUDED.definition;
            """,
            [TYPE_ID],
        )
        for id_nomenclature, mnemonique, label, definition, ordre in TYPES_POSTE:
            cursor.execute(
                """
                INSERT INTO ref_nomenclatures.t_nomenclatures
                    (id_nomenclature, id_type, cd_nomenclature, mnemonique,
                     label, definition, source, statut, hierarchy,
                     date_ajout, date_maj, actif)
                VALUES (%s, %s, %s, %s, %s, %s, 'CICADA', 'Validé', %s,
                        NOW(), NOW(), true)
                ON CONFLICT (id_nomenclature) DO UPDATE SET
                    id_type = EXCLUDED.id_type,
                    cd_nomenclature = EXCLUDED.cd_nomenclature,
                    mnemonique = EXCLUDED.mnemonique,
                    label = EXCLUDED.label,
                    definition = EXCLUDED.definition,
                    hierarchy = EXCLUDED.hierarchy,
                    actif = true;
                """,
                [id_nomenclature, TYPE_ID, mnemonique, mnemonique, label,
                 definition, ordre],
            )


def retirer_nomenclature(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM ref_nomenclatures.t_nomenclatures WHERE id_type = %s;",
            [TYPE_ID],
        )
        cursor.execute(
            "DELETE FROM ref_nomenclatures.bib_nomenclatures_types WHERE id_type = %s;",
            [TYPE_ID],
        )


def _index_par_mnemonique(apps):
    Nomenclature = apps.get_model("core", "Nomenclature")
    return {
        n.mnemonique.upper(): n
        for n in Nomenclature.objects.filter(id_type_id=TYPE_ID)
    }


def basculer_vers_la_nomenclature(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    par_mnemonique = _index_par_mnemonique(apps)

    for fonction in Fonction.objects.all():
        nomenclature = par_mnemonique.get((fonction.type_poste or '').upper())
        if nomenclature is not None:
            fonction.id_type_poste = nomenclature
            fonction.save(update_fields=["id_type_poste"])


def revenir_au_code(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    for fonction in Fonction.objects.select_related("id_type_poste"):
        if fonction.id_type_poste_id:
            fonction.type_poste = (fonction.id_type_poste.mnemonique or '').lower()
            fonction.save(update_fields=["type_poste"])


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0122_socle_garde_animateur"),
        ("core", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed_nomenclature, retirer_nomenclature),
        migrations.AddField(
            model_name="fonction",
            name="id_type_poste",
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_column="id_type_poste",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="fonctions",
                to="core.nomenclature",
                limit_choices_to={"id_type__mnemonique": "TYPE_POSTE"},
                help_text=(
                    "Catégorie de la fonction (nomenclature TYPE_POSTE, #633). "
                    "Conditionne la saisie du coût jour : pas de coût jour pour "
                    "un prestataire, 0 par défaut pour un bénévole."
                ),
                verbose_name="Type de poste",
            ),
        ),
        migrations.RunPython(basculer_vers_la_nomenclature, revenir_au_code),
        migrations.RemoveField(model_name="fonction", name="type_poste"),
    ]
