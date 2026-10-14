"""
Interface d'administration pour les instances
"""
import logging

from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone

from .adhesion import VALIDITE_CODE, empreinte_code, envoyer_code, tirer_code
from .models import AdhesionHub, Heartbeat, Instance

logger = logging.getLogger(__name__)


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ('token_short', 'version', 'last_heartbeat', 'is_active', 
                    'structure_name', 'rgpd_consent')
    list_filter = ('is_active', 'version', 'rgpd_consent', 'last_heartbeat')
    search_fields = ('token', 'admin_email', 'structure_name')
    readonly_fields = ('token', 'first_seen', 'created_at', 'updated_at')
    
    def token_short(self, obj):
        return str(obj.token)[:8] + '...'
    token_short.short_description = 'Token'


@admin.register(Heartbeat)
class HeartbeatAdmin(admin.ModelAdmin):
    list_display = ('instance', 'timestamp', 'version', 'ip_address')
    list_filter = ('timestamp', 'version')
    readonly_fields = ('instance', 'timestamp', 'version', 'ip_address')


RAPPEL_VERIFICATION = (
    "Avant d'envoyer le code, prenez contact avec l'administrateur et vérifiez que l'adresse de "
    "confirmation appartient bien à la structure (de préférence une adresse que RNF connaît déjà, "
    "et non seulement celle déclarée dans la demande)."
)


@admin.register(AdhesionHub)
class AdhesionHubAdmin(admin.ModelAdmin):
    """Traitement, par RNF, des adhésions au hub (#696).

    Pas d'action « Accepter » : RNF décide en envoyant le code de confirmation,
    et c'est la saisie du code juste sur l'instance qui enrôle. Tout est en
    lecture seule sauf l'adresse d'envoi du code et le motif de refus : la
    demande est l'œuvre de l'instance, et les empreintes doivent être enrôlées
    telles qu'elle les a envoyées.
    """
    list_display = ('libelle', 'instance_id_demande', 'contact', 'statut', 'demandee_le',
                    'code_envoye_le', 'code_essais', 'traitee_le')
    list_filter = ('statut',)
    search_fields = ('libelle', 'instance_id_demande', 'contact_nom', 'contact_email')
    actions = ['envoyer_code_confirmation', 'refuser']
    readonly_fields = ('instance', 'instance_id_demande', 'libelle', 'url_publique',
                       'contact_nom', 'contact_email', 'contact_telephone', 'message',
                       'statut', 'empreinte_depot', 'empreinte_lecture', 'hub_url',
                       'code_expire_le', 'code_essais', 'code_envoye_le', 'code_envoye_par',
                       'demandee_le', 'traitee_le', 'traitee_par')
    fieldsets = (
        ('Demande', {'fields': ('instance', 'instance_id_demande', 'libelle', 'url_publique',
                                'demandee_le')}),
        ('Contact', {'fields': ('contact_nom', 'contact_email', 'contact_telephone', 'message')}),
        ('Code de confirmation', {
            'fields': ('email_confirmation', 'code_envoye_le', 'code_envoye_par', 'code_expire_le',
                       'code_essais'),
            'description': RAPPEL_VERIFICATION + " Corrigez l'adresse ci-dessous si besoin, enregistrez, "
                           "puis lancez l'action « Envoyer le code de confirmation » depuis la liste."}),
        ('Décision', {'fields': ('statut', 'motif_refus', 'hub_url', 'traitee_le', 'traitee_par'),
                      'description': "Pour refuser : saisir le motif, enregistrer, puis lancer l'action "
                                     "« Refuser » depuis la liste. Il est affiché à la structure."}),
        ('Empreintes des jetons', {'fields': ('empreinte_depot', 'empreinte_lecture'),
                                   'classes': ('collapse',)}),
    )

    @admin.display(description='contact')
    def contact(self, obj):
        return f"{obj.contact_nom} <{obj.contact_email}>"

    def has_add_permission(self, request):
        # Une demande vient toujours d'une instance, authentifiée par son jeton de
        # suivi : en créer une ici n'aurait pas d'émetteur.
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), 'subtitle': RAPPEL_VERIFICATION}
        return super().changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {**(extra_context or {}), 'subtitle': RAPPEL_VERIFICATION}
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    @admin.action(description="Envoyer le code de confirmation")
    def envoyer_code_confirmation(self, request, queryset):
        """Tire un code, l'envoie par e-mail, puis passe la demande en « code envoyé ».

        Renvoyer un code invalide le précédent et remet le compteur d'essais à
        zéro. Si l'e-mail ne part pas, rien ne change : une demande « code
        envoyé » dont personne n'a reçu le code bloquerait la structure. Le code
        n'est jamais affiché ici — il ne doit exister que dans l'e-mail.
        """
        if not (getattr(settings, 'HUB_URL', '') and getattr(settings, 'HUB_ADMIN_TOKEN', '')):
            # Le code juste échouerait à l'enrôlement : inutile de le faire saisir.
            self.message_user(request, "HUB_URL et HUB_ADMIN_TOKEN doivent être renseignés dans le .env de "
                                       "l'API de suivi avant d'envoyer un code.", messages.ERROR)
            return
        for adhesion in queryset:
            if adhesion.statut not in (AdhesionHub.EN_ATTENTE, AdhesionHub.CODE_ENVOYE):
                self.message_user(request, f"{adhesion} : seule une demande en attente peut recevoir un code.",
                                  messages.WARNING)
                continue
            if not adhesion.email_confirmation:
                self.message_user(request, f"{adhesion} : renseignez d'abord l'adresse d'envoi du code.",
                                  messages.ERROR)
                continue
            code = tirer_code()
            expire_le = timezone.now() + VALIDITE_CODE
            try:
                envoyer_code(adhesion, code, expire_le)
            except Exception as exc:  # noqa: BLE001 — SMTP, réseau
                logger.exception("Adhésion %s : code de confirmation non envoyé", adhesion.pk)
                self.message_user(request, f"{adhesion} : l'e-mail n'a pas pu être envoyé "
                                           f"({exc.__class__.__name__}). Aucun code n'a été émis.",
                                  messages.ERROR)
                continue
            adhesion.code_empreinte = empreinte_code(code)
            adhesion.code_expire_le = expire_le
            adhesion.code_essais = 0
            adhesion.code_envoye_le = timezone.now()
            adhesion.code_envoye_par = request.user.get_username()
            adhesion.statut = AdhesionHub.CODE_ENVOYE
            adhesion.save()
            self.message_user(request, f"{adhesion.libelle} : code de confirmation envoyé à "
                                       f"{adhesion.email_confirmation} (valable 7 jours).", messages.SUCCESS)

    @admin.action(description="Refuser")
    def refuser(self, request, queryset):
        for adhesion in queryset:
            if adhesion.statut not in (AdhesionHub.EN_ATTENTE, AdhesionHub.CODE_ENVOYE):
                # Refuser une adhésion acceptée laisserait l'instance enrôlée sur
                # le hub tout en lui affichant « refusée » : le retrait se fait sur le hub.
                self.message_user(request, f"{adhesion} : seule une demande en attente peut être refusée.",
                                  messages.WARNING)
                continue
            adhesion.statut = AdhesionHub.REFUSEE
            adhesion.traitee_le = timezone.now()
            adhesion.traitee_par = request.user.get_username()
            adhesion.invalider_code()  # un code déjà envoyé ne doit plus enrôler
            adhesion.save()
            if not adhesion.motif_refus:
                self.message_user(request, f"{adhesion.libelle} : refusée sans motif — la structure ne saura "
                                           "pas quoi corriger. Vous pouvez encore en saisir un.",
                                  messages.WARNING)
            else:
                self.message_user(request, f"{adhesion.libelle} : demande refusée.", messages.SUCCESS)
