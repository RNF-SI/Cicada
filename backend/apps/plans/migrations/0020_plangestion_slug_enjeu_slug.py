"""
Add slug fields to PlanGestion and Enjeu models.
Three-step migration:
1. Add nullable slug fields
2. Data migration to generate slugs for existing records
3. Make slug fields non-nullable and add uniqueness constraints
"""
from django.db import migrations, models
from django.utils.text import slugify


def generate_plan_slugs(apps, schema_editor):
    """Generate slugs for all existing PlanGestion records."""
    PlanGestion = apps.get_model('plans', 'PlanGestion')
    existing_slugs = set()

    for plan in PlanGestion.objects.all().order_by('id_pg'):
        base_slug = slugify(plan.nom)
        if not base_slug:
            base_slug = 'plan'
        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        existing_slugs.add(slug)
        PlanGestion.objects.filter(pk=plan.pk).update(slug=slug)


def generate_enjeu_slugs(apps, schema_editor):
    """Generate slugs for all existing Enjeu records."""
    Enjeu = apps.get_model('plans', 'Enjeu')
    # Track slugs per plan
    plan_slugs = {}

    for enjeu in Enjeu.objects.all().order_by('id_enjeu'):
        plan_id = enjeu.id_pg_id
        if plan_id not in plan_slugs:
            plan_slugs[plan_id] = set()

        source = enjeu.intitule_court or enjeu.libelle
        base_slug = slugify(source)
        if not base_slug:
            base_slug = 'enjeu'
        slug = base_slug
        counter = 2
        while slug in plan_slugs[plan_id]:
            slug = f"{base_slug}-{counter}"
            counter += 1
        plan_slugs[plan_id].add(slug)
        Enjeu.objects.filter(pk=enjeu.pk).update(slug=slug)


def reverse_noop(apps, schema_editor):
    """No-op reverse for data migration."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0019_alter_indicateur_table_comment_and_more'),
    ]

    operations = [
        # Step 1: Add nullable slug fields (db_index=False to avoid _like index
        # that would conflict with the AlterField unique=True step later)
        migrations.AddField(
            model_name='plangestion',
            name='slug',
            field=models.SlugField(
                help_text='Identifiant URL lisible, généré automatiquement depuis le nom',
                max_length=300,
                null=True,
                db_index=False,
                verbose_name='Slug',
            ),
        ),
        migrations.AddField(
            model_name='enjeu',
            name='slug',
            field=models.SlugField(
                help_text='Identifiant URL lisible, généré automatiquement',
                max_length=300,
                null=True,
                db_index=False,
                verbose_name='Slug',
            ),
        ),

        # Step 2: Data migration - generate slugs for existing records
        migrations.RunPython(generate_plan_slugs, reverse_noop),
        migrations.RunPython(generate_enjeu_slugs, reverse_noop),

        # Step 3: Make slug non-nullable and add uniqueness constraints
        migrations.AlterField(
            model_name='plangestion',
            name='slug',
            field=models.SlugField(
                help_text='Identifiant URL lisible, généré automatiquement depuis le nom',
                max_length=300,
                unique=True,
                verbose_name='Slug',
            ),
        ),
        migrations.AlterField(
            model_name='plangestion',
            name='nom',
            field=models.CharField(
                max_length=255,
                unique=True,
                verbose_name='Nom du plan de gestion',
            ),
        ),
        migrations.AlterField(
            model_name='enjeu',
            name='slug',
            field=models.SlugField(
                help_text='Identifiant URL lisible, généré automatiquement',
                max_length=300,
                verbose_name='Slug',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='enjeu',
            unique_together={('id_pg', 'slug'), ('id_pg', 'libelle')},
        ),
    ]
