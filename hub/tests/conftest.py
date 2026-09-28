import pytest


@pytest.fixture
def plan(db):
    """Un plan publié minimal, tel qu'une instance en déposerait un."""
    from apps.index.models import PlanIndexe

    return PlanIndexe.objects.create(
        instance_id='rnf',
        id_pg=42,
        slug='camargue-2020-2030',
        nom='Plan de gestion de la Camargue 2020-2030',
        statut='valide',
        annee_debut=2020,
        annee_fin=2030,
        gestionnaire_principal='Réserves Naturelles de France',
        sites=[{'nom_site': 'Camargue', 'slug': 'camargue', 'id_inpn': 'FR3600001'}],
        site_inpn_codes=['FR3600001'],
        type_site_codes=['RNN'],
    )
