from django.db import migrations, models
import django.core.validators


def reset_default_header_color(apps, schema_editor):
    """#448 — Le bandeau redevient blanc par défaut. Les configurations qui
    portent encore l'ancien défaut automatique (#025359, jamais choisi
    explicitement par un admin puisque la fonctionnalité est récente) sont
    repassées en blanc."""
    SiteConfiguration = apps.get_model('core', 'SiteConfiguration')
    SiteConfiguration.objects.filter(header_color__iexact='#025359').update(
        header_color='#FFFFFF'
    )


def restore_old_default(apps, schema_editor):
    SiteConfiguration = apps.get_model('core', 'SiteConfiguration')
    SiteConfiguration.objects.filter(header_color__iexact='#FFFFFF').update(
        header_color='#025359'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_siteconfiguration_header_color_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='siteconfiguration',
            name='header_color',
            field=models.CharField(
                default='#FFFFFF',
                help_text='Couleur de fond du bandeau (header), au format hexadécimal #RRGGBB',
                max_length=7,
                validators=[django.core.validators.RegexValidator(
                    message='La couleur doit être au format hexadécimal (ex. #025359).',
                    regex='^#[0-9A-Fa-f]{6}$',
                )],
                verbose_name='Couleur du bandeau',
            ),
        ),
        migrations.RunPython(reset_default_header_color, restore_old_default),
    ]
