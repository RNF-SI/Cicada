"""Jeton de suivi en empreinte (#697), 1/2 : calcul des empreintes et nouveaux identifiants.

Le jeton de chaque instance était sa clé primaire, en clair. On calcule son
empreinte SHA-256 (forme canonique : UUID en minuscules, comme
`Instance.empreinte_jeton`), puis on remplace la clé primaire par un UUID tiré au
hasard, sans rapport avec le jeton — heartbeats et adhésions suivent. Les
contraintes de clé étrangère de Django sont différées : la transaction peut
réécrire la clé primaire et ses références avant de les vérifier.

Retour arrière : la structure se rétablit (0004 inversée), pas les jetons — ils
ne sont plus en base. Les instances se réenregistreraient alors au heartbeat
suivant (401 → register), sous une nouvelle ligne.

Migration séparée de 0004 : PostgreSQL refuse de modifier une table qui a des
vérifications de contraintes en attente dans la même transaction.
"""
from django.db import migrations, models

CALCUL = """
SET CONSTRAINTS ALL DEFERRED;
UPDATE tracking_instances SET token_empreinte = encode(sha256(convert_to(token::text, 'UTF8')), 'hex');
CREATE TEMP TABLE _instances_ids ON COMMIT DROP AS
    SELECT token AS ancien, gen_random_uuid() AS nouveau FROM tracking_instances;
UPDATE tracking_heartbeats h SET instance_id = m.nouveau FROM _instances_ids m WHERE h.instance_id = m.ancien;
UPDATE tracking_adhesions_hub a SET instance_id = m.nouveau FROM _instances_ids m WHERE a.instance_id = m.ancien;
UPDATE tracking_instances i SET token = m.nouveau FROM _instances_ids m WHERE i.token = m.ancien;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('instances', '0002_adhesion_hub'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='token_empreinte',
            field=models.CharField(editable=False, max_length=64, null=True, verbose_name='empreinte du jeton'),
        ),
        migrations.RunSQL(CALCUL, migrations.RunSQL.noop),
    ]
