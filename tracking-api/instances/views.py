"""
Vues API pour le suivi des instances
"""
import ipaddress
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.throttling import UserRateThrottle
from rest_framework.permissions import IsAdminUser, AllowAny
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .adhesion import (ESSAIS_MAX, EchecEnrolement, code_correct, enroler_sur_hub,
                       envoyer_message_contact, notifier_nouvelle_demande, normaliser_code)
from .models import AdhesionHub, Instance
from .serializers import (ConfirmationSerializer, ContactSerializer, DeclarationSerializer,
                          DemandeAdhesionSerializer, InstanceSerializer)
from tracking.settings import LATEST_VERSION

logger = logging.getLogger(__name__)


class HeartbeatThrottle(UserRateThrottle):
    rate = '5/day'  # Permet les retries en cas d'échec


class RegisterThrottle(UserRateThrottle):
    rate = '10/hour'


class ContactThrottle(UserRateThrottle):
    # Portée propre : sans elle, le compteur serait partagé avec les autres
    # limites « user » de la même instance.
    scope = 'contact_rnf'
    rate = '10/day'


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
    """IP du client, vue par le reverse proxy de confiance (#697).

    X-Forwarded-For est en partie écrit par le client : Apache *ajoute* l'IP qu'il
    voit à la valeur reçue. Seules les NUM_PROXIES dernières valeurs sont donc
    fiables, et l'on retient la plus éloignée d'entre elles — même règle que les
    limites de débit de DRF, pour que l'IP journalisée soit celle qui est limitée.
    Sans proxy (NUM_PROXIES = 0), l'en-tête est ignoré.
    """
    remote = request.META.get('REMOTE_ADDR')
    nb_proxies = api_settings.NUM_PROXIES or 0
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if nb_proxies > 0 and xff:
        adresses = [a.strip() for a in xff.split(',') if a.strip()]
        if adresses:
            candidate = adresses[-min(nb_proxies, len(adresses))]
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass
    return remote


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
def register_instance(request):
    """Enregistre une nouvelle instance (sans auth : le jeton, dans le corps, est tiré par l'instance).

    N'écrit que pour un jeton inconnu (#697). Sur un jeton déjà enregistré, rien
    n'est modifié : connaître le jeton d'une instance ne doit pas suffire à
    réécrire sa structure, son e-mail ou son IP par une route ouverte. Ces
    mises à jour passent par PATCH /instances/me/ (jeton en en-tête), la version
    et l'IP par le heartbeat.
    """
    data = request.data
    ip = get_client_ip(request)
    try:
        empreinte = Instance.empreinte_jeton(data.get('token') or '')
    except ValueError:
        return Response({'error': 'Token requis (UUID)'}, status=400)

    if Instance.objects.filter(token_empreinte=empreinte).exists():
        logger.info("Enregistrement sur un jeton déjà connu, ignoré (IP %s)", ip)
        return Response({'status': 'already_registered'}, status=200)

    instance = Instance(token_empreinte=empreinte, version=data.get('version', 'unknown'), ip_address=ip,
                        rgpd_consent=bool(data.get('rgpd_consent', False)))
    if instance.rgpd_consent:
        instance.admin_name = data.get('admin_name')
        instance.admin_email = data.get('admin_email')
        instance.structure_name = data.get('structure_name')
        instance.rgpd_consent_date = timezone.now()
    instance.save()
    logger.info("Instance %s enregistrée (v%s, IP %s, structure déclarée : %s)",
                instance.id_court, instance.version, ip, instance.structure_name or '—')

    # Le jeton n'est pas renvoyé : l'instance le connaît, et il n'a rien à faire
    # dans une réponse qu'un proxy ou un journal pourrait garder.
    return Response({'status': 'registered'}, status=201)


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


def _effacer_donnees_personnelles(instance):
    instance.admin_name = None
    instance.admin_email = None
    instance.structure_name = None
    instance.rgpd_consent = False
    instance.rgpd_withdrawal_date = timezone.now()


@api_view(['GET', 'PATCH', 'DELETE'])
def instance_me(request):
    """Infos (GET), mise à jour des coordonnées déclarées (PATCH) ou effacement RGPD (DELETE)."""
    instance = request.user

    if request.method == 'DELETE':
        # Droit à l'effacement RGPD
        _effacer_donnees_personnelles(instance)
        instance.save()

        return Response({
            'status': 'deleted',
            'message': 'Données personnelles supprimées'
        })

    if request.method == 'PATCH':
        # Seule route qui modifie structure et contact (#697) : authentifiée par
        # le jeton, refusée à une instance désactivée par RNF.
        serializer = DeclarationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        if donnees['rgpd_consent']:
            if not instance.rgpd_consent:
                instance.rgpd_consent_date = timezone.now()
            instance.rgpd_consent = True
            for champ in ('admin_name', 'admin_email', 'structure_name'):
                if champ in donnees:
                    setattr(instance, champ, donnees[champ] or None)
        else:
            _effacer_donnees_personnelles(instance)
        instance.save()
        logger.info("Instance %s : coordonnées mises à jour (IP %s, structure déclarée : %s)",
                    instance.id_court, get_client_ip(request), instance.structure_name or '—')

    return Response(InstanceSerializer(instance).data)


@api_view(['GET', 'POST'])
def adhesion_hub(request):
    """Demande d'adhésion au hub (POST) et son état (GET), pour l'instance authentifiée (#696).

    L'instance qui demande est celle du jeton X-Instance-Token, jamais une
    instance désignée dans le corps : une structure ne peut demander que pour
    elle-même.
    """
    instance = request.user

    if request.method == 'GET':
        adhesion = AdhesionHub.objects.filter(instance=instance).first()
        if adhesion is None:
            return Response({'detail': "Aucune demande d'adhésion."}, status=404)
        acceptee = adhesion.statut == AdhesionHub.ACCEPTEE
        return Response({
            'statut': adhesion.statut,
            'instance_id': adhesion.instance_id_demande,
            'hub_url': adhesion.hub_url if acceptee else '',
            'motif_refus': adhesion.motif_refus,
            'demandee_le': adhesion.demandee_le.isoformat(),
            'traitee_le': adhesion.traitee_le.isoformat() if adhesion.traitee_le else None,
            # L'échéance, jamais le code : l'instance doit le recevoir par e-mail.
            'code_expire_le': (adhesion.code_expire_le.isoformat()
                               if adhesion.statut == AdhesionHub.CODE_ENVOYE and adhesion.code_expire_le
                               else None),
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
    adhesion.contact_nom = donnees['contact_nom']
    adhesion.contact_email = donnees['contact_email']
    adhesion.contact_telephone = donnees['contact_telephone']
    adhesion.message = donnees['message']
    adhesion.email_confirmation = donnees['contact_email']
    # Une demande refusée puis renouvelée repart de zéro : l'ancien refus ne
    # doit pas rester affiché comme s'il portait sur la nouvelle demande, et un
    # code déjà envoyé portait sur d'autres empreintes — il ne doit plus valoir.
    adhesion.invalider_code()
    adhesion.code_envoye_le = None
    adhesion.code_envoye_par = ''
    adhesion.statut = AdhesionHub.EN_ATTENTE
    adhesion.motif_refus = ''
    adhesion.hub_url = ''
    adhesion.demandee_le = timezone.now()
    adhesion.traitee_le = None
    adhesion.traitee_par = ''
    adhesion.save()
    notifier_nouvelle_demande(adhesion)

    return Response({
        'statut': adhesion.statut,
        'demandee_le': adhesion.demandee_le.isoformat(),
    }, status=201)


@api_view(['POST'])
def adhesion_hub_confirmation(request):
    """Saisie du code de confirmation envoyé par RNF ; un code juste enrôle l'instance.

    La demande est verrouillée (select_for_update) le temps de la vérification et
    de l'enrôlement : deux saisies simultanées ne peuvent pas dépasser le
    compteur d'essais, ni enrôler deux fois.

    Le code n'est consommé qu'au succès complet : si le hub échoue, il reste
    valable et l'administrateur réessaie plus tard. Jamais de code ni
    d'empreinte dans la réponse ou le journal.
    """
    serializer = ConfirmationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    code = serializer.validated_data['code']

    with transaction.atomic():
        adhesion = AdhesionHub.objects.select_for_update().filter(instance=request.user).first()
        if adhesion is None:
            return Response({'detail': "Aucune demande d'adhésion."}, status=404)
        if adhesion.statut != AdhesionHub.CODE_ENVOYE or not adhesion.code_empreinte:
            return Response({'erreur': 'pas_de_code'}, status=409)
        if adhesion.code_expire_le and adhesion.code_expire_le <= timezone.now():
            return Response({'erreur': 'code_expire'}, status=400)

        if not code_correct(adhesion, code):
            if not normaliser_code(code):
                # Rien de saisi : ce n'est pas une tentative.
                return Response({'erreur': 'code_invalide',
                                 'essais_restants': ESSAIS_MAX - adhesion.code_essais}, status=400)
            adhesion.code_essais += 1
            if adhesion.code_essais >= ESSAIS_MAX:
                # Code invalidé : RNF doit en renvoyer un.
                adhesion.invalider_code()
                adhesion.statut = AdhesionHub.EN_ATTENTE
                adhesion.save()
                logger.warning("Adhésion %s : code invalidé après %d essais erronés", adhesion.pk, ESSAIS_MAX)
                return Response({'erreur': 'trop_d_essais'}, status=400)
            adhesion.save(update_fields=['code_essais'])
            return Response({'erreur': 'code_invalide',
                             'essais_restants': ESSAIS_MAX - adhesion.code_essais}, status=400)

        try:
            hub_url = enroler_sur_hub(adhesion)
        except EchecEnrolement as exc:
            logger.error("Adhésion %s : code juste mais enrôlement impossible — %s", adhesion.pk, exc)
            return Response({'erreur': 'hub_injoignable'}, status=502)

        adhesion.statut = AdhesionHub.ACCEPTEE
        adhesion.hub_url = hub_url
        adhesion.motif_refus = ''
        adhesion.traitee_le = timezone.now()
        adhesion.traitee_par = 'code'
        adhesion.invalider_code()
        adhesion.save()

    return Response({'statut': adhesion.statut, 'hub_url': adhesion.hub_url})


@api_view(['POST'])
@throttle_classes([ContactThrottle])
def contact_rnf(request):
    """Message libre de l'administrateur d'une instance à RNF (Reply-To = son adresse).

    Contrairement à l'accusé de réception d'une demande, l'e-mail est ici tout
    le contenu de la requête : s'il ne part pas, le dire plutôt que de laisser
    croire que RNF l'a reçu.
    """
    serializer = ContactSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    donnees = serializer.validated_data
    adhesion = AdhesionHub.objects.filter(instance=request.user).first()
    try:
        envoyer_message_contact(request.user, adhesion, donnees['nom'], donnees['email'],
                                donnees['sujet'], donnees['message'])
    except Exception:  # noqa: BLE001 — SMTP, réseau
        logger.exception("Message de contact de l'instance %s non envoyé", request.user.id_court)
        return Response({'erreur': 'envoi_impossible'}, status=502)
    return Response({'statut': 'envoye'}, status=202)


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
