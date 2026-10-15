"""Jeton de suivi en empreinte (#697), 2/2 : l'ancienne colonne `token` devient l'identifiant opaque `id`."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('instances', '0003_empreinte_jeton_suivi'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instance',
            name='token_empreinte',
            field=models.CharField(editable=False, max_length=64, unique=True, verbose_name='empreinte du jeton'),
        ),
        migrations.RenameField(
            model_name='instance',
            old_name='token',
            new_name='id',
        ),
    ]
