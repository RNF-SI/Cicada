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
from .models import Instance
from .serializers import InstanceSerializer
from tracking.settings import LATEST_VERSION


class HeartbeatThrottle(UserRateThrottle):
    rate = '5/day'  # Permet les retries en cas d'échec


class RegisterThrottle(UserRateThrottle):
    rate = '10/hour'


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

    update_available = instance.version != LATEST_VERSION

    return Response({
        'status': 'ok',
        'last_heartbeat': instance.last_heartbeat.isoformat(),
        'update_available': update_available,
        'latest_version': LATEST_VERSION,
    })


@api_view(['GET'])
def check_version(request):
    """Vérifie si une mise à jour est disponible"""
    current = request.query_params.get('current_version', '')

    return Response({
        'current_version': current,
        'latest_version': LATEST_VERSION,
        'update_available': current != LATEST_VERSION,
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
