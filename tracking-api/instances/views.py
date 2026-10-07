"""
Vues API pour le suivi des instances
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.permissions import IsAdminUser, AllowAny
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .adhesion import code_verification
from .models import AdhesionHub, Instance
from .serializers import DemandeAdhesionSerializer, InstanceSerializer
from tracking.settings import LATEST_VERSION


class HeartbeatThrottle(UserRateThrottle):
    rate = '5/day'  # Permet les retries en cas d'échec


class RegisterThrottle(UserRateThrottle):
    rate = '10/hour'


def _version_key(version):
    """« 0.1.49 » → (0, 1, 49) ; None si la version n'est pas numérique."""
    try:
        return tuple(int(part) for part in str(version).split('.'))
    except (TypeError, ValueError):
        return None


def is_update_available(current):
    """Vrai seulement si LATEST_VERSION est renseignée et plus récente que
    la version de l'instance (une instance en avance n'a rien à mettre à jour)."""
    latest, installed = _version_key(LATEST_VERSION), _version_key(current)
    return bool(latest and installed and latest > installed)


def get_client_ip(request):
    """Récupère l'IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
def register_instance(request):
    """Enregistre ou met à jour une instance (sans auth : le token dans le body identifie l'instance)."""
    data = request.data
    token = data.get('token')

    if not token:
        return Response({'error': 'Token requis'}, status=400)

    instance_data = {
        'version': data.get('version', 'unknown'),
        'ip_address': get_client_ip(request),
        'rgpd_consent': data.get('rgpd_consent', False),
    }

    if data.get('rgpd_consent'):
        instance_data.update({
            'admin_name': data.get('admin_name'),
            'admin_email': data.get('admin_email'),
            'structure_name': data.get('structure_name'),
            'rgpd_consent_date': timezone.now(),
        })

    instance, created = Instance.objects.update_or_create(
        token=token,
        defaults=instance_data
    )

    return Response({
        'status': 'registered' if created else 'updated',
        'token': str(instance.token),
    }, status=201 if created else 200)


@csrf_exempt
@api_view(['POST'])
@throttle_classes([HeartbeatThrottle])
def heartbeat(request):
    """Heartbeat quotidien d'une instance"""
    instance = request.user  # Authentifié via InstanceTokenAuthentication

    instance.last_heartbeat = timezone.now()
    instance.version = request.data.get('version', instance.version)
    instance.ip_address = get_client_ip(request)
    instance.save()

    update_available = is_update_available(instance.version)

    return Response({
        'status': 'ok',
        'last_heartbeat': instance.last_heartbeat.isoformat(),
        'update_available': update_available,
        'latest_version': LATEST_VERSION or None,
    })


@api_view(['GET'])
def check_version(request):
    """Vérifie si une mise à jour est disponible"""
    current = request.query_params.get('current_version', '')

    return Response({
        'current_version': current,
        'latest_version': LATEST_VERSION or None,
        'update_available': is_update_available(current),
    })


@api_view(['GET', 'DELETE'])
def instance_me(request):
    """Infos ou suppression des données personnelles"""
    instance = request.user

    if request.method == 'DELETE':
        # Droit à l'effacement RGPD
        instance.admin_name = None
        instance.admin_email = None
        instance.structure_name = None
        instance.rgpd_consent = False
        instance.rgpd_withdrawal_date = timezone.now()
        instance.save()

        return Response({
            'status': 'deleted',
            'message': 'Données personnelles supprimées'
        })

    return Response(InstanceSerializer(instance).data)


@api_view(['GET', 'POST'])
def adhesion_hub(request):
    """Demande d'adhésion au hub (POST) et son état (GET), pour l'instance authentifiée (#696).

    L'instance qui demande est celle du jeton X-Instance-Token, jamais une
    instance désignée dans le corps : une structure ne peut demander que pour
    elle-même. Le code est recalculé ici, à partir de ce jeton, pour que la
    comparaison de vive voix prouve que la demande vient bien de cette instance.
    """
    instance = request.user

    if request.method == 'GET':
        adhesion = AdhesionHub.objects.filter(instance=instance).first()
        if adhesion is None:
            return Response({'detail': "Aucune demande d'adhésion."}, status=404)
        acceptee = adhesion.statut == AdhesionHub.ACCEPTEE
        return Response({
            'statut': adhesion.statut,
            'code': adhesion.code,
            'instance_id': adhesion.instance_id_demande,
            'hub_url': adhesion.hub_url if acceptee else '',
            'motif_refus': adhesion.motif_refus,
            'demandee_le': adhesion.demandee_le.isoformat(),
            'traitee_le': adhesion.traitee_le.isoformat() if adhesion.traitee_le else None,
        })

    serializer = DemandeAdhesionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    donnees = serializer.validated_data

    existante = AdhesionHub.objects.filter(instance=instance).first()
    if existante and existante.statut == AdhesionHub.ACCEPTEE:
        # L'instance est enrôlée : une nouvelle demande changerait des empreintes
        # que le hub ne connaît pas, et la demande « acceptée » mentirait.
        return Response({'detail': "Adhésion déjà acceptée : contactez RNF pour la modifier."},
                        status=409)
    if AdhesionHub.objects.filter(instance_id_demande=donnees['instance_id'],
                                  statut=AdhesionHub.ACCEPTEE).exclude(instance=instance).exists():
        # Le hub refuserait de toute façon (409) ; le dire dès la demande évite à
        # RNF d'appeler une structure pour un identifiant déjà pris.
        return Response({'detail': "Cet identifiant est déjà utilisé par une autre instance enrôlée."},
                        status=409)

    adhesion = existante or AdhesionHub(instance=instance)
    adhesion.instance_id_demande = donnees['instance_id']
    adhesion.libelle = donnees['libelle']
    adhesion.url_publique = donnees['url_publique']
    adhesion.empreinte_depot = donnees['empreinte_depot']
    adhesion.empreinte_lecture = donnees['empreinte_lecture']
    adhesion.code = code_verification(str(instance.token), donnees['instance_id'],
                                      donnees['empreinte_depot'], donnees['empreinte_lecture'])
    # Une demande refusée puis renouvelée repart de zéro : l'ancien refus ne
    # doit pas rester affiché comme s'il portait sur la nouvelle demande.
    adhesion.statut = AdhesionHub.EN_ATTENTE
    adhesion.motif_refus = ''
    adhesion.hub_url = ''
    adhesion.demandee_le = timezone.now()
    adhesion.traitee_le = None
    adhesion.traitee_par = ''
    adhesion.save()

    return Response({
        'statut': adhesion.statut,
        'code': adhesion.code,
        'demandee_le': adhesion.demandee_le.isoformat(),
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats(request):
    """Statistiques pour l'admin"""
    total = Instance.objects.count()
    active = Instance.objects.filter(is_active=True).count()
    
    # Compter par version
    from django.db.models import Count
    versions = Instance.objects.values('version').annotate(count=Count('version'))
    
    return Response({
        'total_instances': total,
        'active_instances': active,
        'inactive_instances': total - active,
        'instances_by_version': {v['version']: v['count'] for v in versions},
        'instances_with_rgpd_consent': Instance.objects.filter(rgpd_consent=True).count(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_instances(request):
    """Liste des instances pour l'admin"""
    instances = Instance.objects.all()
    
    # Filtres
    if request.query_params.get('is_active'):
        instances = instances.filter(is_active=request.query_params.get('is_active') == 'true')
    if request.query_params.get('version'):
        instances = instances.filter(version=request.query_params.get('version'))
    
    serializer = InstanceSerializer(instances, many=True)
    return Response({
        'count': len(serializer.data),
        'results': serializer.data
    })
