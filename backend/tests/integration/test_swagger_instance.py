"""
#750 — Swagger UI de l'instance (/api/docs/).

La page et le schéma exigeaient une session authentifiée, que le navigateur
n'a jamais : le jeton JWT de CICADA vit dans le localStorage de l'application
et n'est pas envoyé à cette page, qui répondait donc toujours 401. Le schéma
est de toute façon publié en clair dans la documentation (/aide/api/) : la page
et le schéma s'ouvrent sans connexion, et ce sont les appels qui restent
protégés, avec le jeton saisi dans « Authorize ».
"""
import pytest
from rest_framework.test import APIClient

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_page_swagger_ouverte_sans_connexion():
    reponse = APIClient().get('/api/docs/')
    assert reponse.status_code == 200
    assert b'swagger-ui' in reponse.content
    # Le jeton saisi dans « Authorize » survit au rechargement de la page.
    assert b'"persistAuthorization": true' in reponse.content


def test_schema_ouvert_sans_connexion_et_annonce_le_jeton():
    reponse = APIClient().get('/api/schema/', {'format': 'json'})
    assert reponse.status_code == 200
    schema = reponse.json()
    assert schema['components']['securitySchemes']['jwtAuth']['scheme'] == 'bearer'
    # Le schéma est complet, pas réduit à ce qu'un anonyme pourrait appeler.
    assert '/api/plans/plans/' in schema['paths']


def test_les_appels_restent_proteges():
    assert APIClient().get('/api/plans/plans/').status_code == 401
