"""
Page « Référentiels de données » (#778) : pour Gestref (types d'action),
PressRef (types de pression), TaxRef et HabRef, la version en service sur
l'instance et le téléchargement des données en CSV (séparateur « ; », UTF-8
avec BOM, lisible par un tableur).

- `GET /api/plans/referentiels/donnees/`
- `GET /api/plans/referentiels/donnees/<code>/csv/` (en flux : TaxRef complet
  compte ~700 000 lignes)
"""
import csv

from django.http import StreamingHttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import referentiel_actions as ra
from .referentiels import moteur

SOURCES = {
    'TAXREF': 'https://inpn.mnhn.fr/telechargement/referentielEspece/taxref',
    'HABREF': 'https://inpn.mnhn.fr/telechargement/referentiels/habitats',
}


def _version(code) -> dict:
    if code == 'TYPE_ACTION':
        v = ra.version_courante()
        return {'code': v.code if v else ra.VERSION_INITIALE,
                'libelle': v.libelle if v else ra.LIBELLE_INITIAL}
    c, l = moteur.version_en_service(moteur.referentiel(code))
    return {'code': c, 'libelle': l}


def _lignes(code):
    """(en-tête, itérateur de lignes) du référentiel en service."""
    from apps.core.models import Nomenclature

    if code == 'TYPE_ACTION':
        categories = dict(Nomenclature.objects.filter(
            id_type__mnemonique='CATEGORIE_ACTION_RESERVE', actif=True)
            .values_list('cd_nomenclature', 'label'))
        qs = (Nomenclature.objects.filter(id_type__mnemonique='TYPE_ACTION', actif=True)
              .order_by('hierarchy', 'cd_nomenclature'))
        return (['code', 'libelle', 'categorie', 'libelle_categorie'],
                ([n.cd_nomenclature, n.label, ra.categorie_du_code(n.cd_nomenclature or ''),
                  categories.get(ra.categorie_du_code(n.cd_nomenclature or ''), '')]
                 for n in qs.iterator()))
    if code == 'PRESSREF':
        qs = (Nomenclature.objects.filter(id_type__mnemonique='TYPE_PRESSION', actif=True)
              .order_by('hierarchy', 'cd_nomenclature'))
        return (['code', 'libelle', 'definition'],
                ([n.cd_nomenclature, n.label, n.definition or ''] for n in qs.iterator()))
    if code == 'TAXREF':
        from apps.taxonomy.models import Taxref
        champs = ['cd_nom', 'cd_ref', 'nom_complet', 'lb_nom', 'lb_auteur', 'nom_vern', 'id_rang',
                  'regne', 'classe', 'ordre', 'famille', 'group2_inpn']
        return champs, Taxref.objects.order_by('cd_nom').values_list(*champs).iterator(chunk_size=5000)
    if code == 'HABREF':
        from apps.habitats.models import Habref
        champs = ['cd_hab', 'cd_typo', 'lb_code', 'lb_hab_fr', 'niveau', 'cd_hab_sup', 'fg_validite']
        return champs, Habref.objects.order_by('cd_hab').values_list(*champs).iterator(chunk_size=5000)
    return None


def _nombre(code) -> int:
    from apps.core.models import Nomenclature
    if code == 'TYPE_ACTION':
        return Nomenclature.objects.filter(id_type__mnemonique='TYPE_ACTION', actif=True).count()
    if code == 'PRESSREF':
        return Nomenclature.objects.filter(id_type__mnemonique='TYPE_PRESSION', actif=True).count()
    if code == 'TAXREF':
        from apps.taxonomy.models import Taxref
        return Taxref.objects.count()
    from apps.habitats.models import Habref
    return Habref.objects.count()


LIBELLES = {
    'TYPE_ACTION': "Types d'action (Gestref)",
    'PRESSREF': 'Types de pression (PressRef)',
    'TAXREF': 'Taxons (TaxRef)',
    'HABREF': 'Habitats (HabRef)',
}


class ReferentielsDonneesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['referentiels'], summary="Référentiels de données : versions (#778)",
                   responses={200: OpenApiResponse(description="Liste des référentiels")})
    def get(self, request):
        return Response({'referentiels': [
            {'code': code, 'libelle': libelle, 'version': _version(code), 'nombre': _nombre(code),
             'source_url': SOURCES.get(code)}
            for code, libelle in LIBELLES.items()]})


class _Tampon:
    def write(self, valeur):
        return valeur


class ReferentielDonneesCsvView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['referentiels'], summary="Télécharger un référentiel en CSV (#778)",
                   responses={200: OpenApiResponse(description="Fichier CSV"),
                              404: OpenApiResponse(description="Référentiel inconnu")})
    def get(self, request, code):
        code = code.upper()
        donnees = _lignes(code) if code in LIBELLES else None
        if donnees is None:
            return Response({'detail': "Référentiel inconnu."}, status=status.HTTP_404_NOT_FOUND)
        entete, lignes = donnees
        ecrivain = csv.writer(_Tampon(), delimiter=';')

        def flux():
            yield '﻿' + ecrivain.writerow(entete)
            for ligne in lignes:
                yield ecrivain.writerow(['' if v is None else v for v in ligne])

        version = _version(code)['code'].lower()
        reponse = StreamingHttpResponse(flux(), content_type='text/csv; charset=utf-8')
        reponse['Content-Disposition'] = f'attachment; filename="{version}.csv"'
        return reponse
