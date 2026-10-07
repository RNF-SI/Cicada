"""
Interface d'administration pour les instances
"""
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .adhesion import EchecEnrolement, enroler_sur_hub
from .models import AdhesionHub, Heartbeat, Instance


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


RAPPEL_CODE = ("Comparez ce code de vive voix avec la structure avant d'accepter : "
               "c'est la seule preuve que la demande vient bien d'elle.")


@admin.register(AdhesionHub)
class AdhesionHubAdmin(admin.ModelAdmin):
    """Validation manuelle, par RNF, des adhésions au hub (#696).

    Le code de vérification est mis en évidence partout où une décision se
    prend : sans la comparaison de vive voix, accepter reviendrait à enrôler
    quiconque connaît un jeton de suivi et le nom d'une structure.
    Tout est en lecture seule sauf le motif de refus : la demande est l'œuvre de
    l'instance, la modifier ici ferait diverger le code des deux côtés.
    """
    list_display = ('libelle', 'instance_id_demande', 'code_affiche', 'statut', 'demandee_le', 'traitee_le')
    list_filter = ('statut',)
    search_fields = ('libelle', 'instance_id_demande', 'code')
    actions = ['accepter', 'refuser']
    readonly_fields = ('code_en_evidence', 'instance', 'instance_id_demande', 'libelle', 'url_publique',
                       'statut', 'empreinte_depot', 'empreinte_lecture', 'hub_url',
                       'demandee_le', 'traitee_le', 'traitee_par')
    fieldsets = (
        ('Code de vérification', {'fields': ('code_en_evidence',), 'description': RAPPEL_CODE}),
        ('Demande', {'fields': ('instance', 'instance_id_demande', 'libelle', 'url_publique',
                                'demandee_le')}),
        ('Décision', {'fields': ('statut', 'motif_refus', 'hub_url', 'traitee_le', 'traitee_par'),
                      'description': "Pour refuser : saisir le motif, enregistrer, puis lancer l'action "
                                     "« Refuser » depuis la liste. Il est affiché à la structure."}),
        ('Empreintes des jetons', {'fields': ('empreinte_depot', 'empreinte_lecture'),
                                   'classes': ('collapse',)}),
    )

    def has_add_permission(self, request):
        # Une demande vient toujours d'une instance : en créer une ici n'aurait
        # pas de code vérifiable par la structure.
        return False

    @admin.display(description='Code', ordering='code')
    def code_affiche(self, obj):
        return format_html('<strong style="font-family:monospace;font-size:1.2em;letter-spacing:.1em">{}</strong>',
                           obj.code)

    @admin.display(description='Code de vérification')
    def code_en_evidence(self, obj):
        return format_html(
            '<div style="font-family:monospace;font-size:2.4em;font-weight:bold;letter-spacing:.15em">{}</div>'
            '<p><strong>{}</strong></p>', obj.code, RAPPEL_CODE)

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), 'subtitle': RAPPEL_CODE}
        return super().changelist_view(request, extra_context=extra_context)

    def _traiter(self, adhesion, request, statut):
        adhesion.statut = statut
        adhesion.traitee_le = timezone.now()
        adhesion.traitee_par = request.user.get_username()

    @admin.action(description="Accepter et enrôler sur le hub (après comparaison du code de vive voix)")
    def accepter(self, request, queryset):
        for adhesion in queryset:
            if adhesion.statut != AdhesionHub.EN_ATTENTE:
                self.message_user(request, f"{adhesion} : seule une demande en attente peut être acceptée.",
                                  messages.WARNING)
                continue
            try:
                hub_url = enroler_sur_hub(adhesion)
            except EchecEnrolement as exc:
                # La demande reste en attente : on ne déclare pas « acceptée »
                # une instance que le hub ne connaît pas.
                self.message_user(request, f"{adhesion} : enrôlement impossible. {exc}", messages.ERROR)
                continue
            self._traiter(adhesion, request, AdhesionHub.ACCEPTEE)
            adhesion.hub_url = hub_url
            adhesion.motif_refus = ''
            adhesion.save()
            self.message_user(request, f"{adhesion.libelle} ({adhesion.instance_id_demande}) est enrôlée "
                                       f"sur le hub (code {adhesion.code}).", messages.SUCCESS)

    @admin.action(description="Refuser")
    def refuser(self, request, queryset):
        for adhesion in queryset:
            if adhesion.statut != AdhesionHub.EN_ATTENTE:
                # Refuser une adhésion acceptée laisserait l'instance enrôlée sur
                # le hub tout en lui affichant « refusée » : le retrait se fait sur le hub.
                self.message_user(request, f"{adhesion} : seule une demande en attente peut être refusée.",
                                  messages.WARNING)
                continue
            self._traiter(adhesion, request, AdhesionHub.REFUSEE)
            adhesion.save()
            if not adhesion.motif_refus:
                self.message_user(request, f"{adhesion.libelle} : refusée sans motif — la structure ne saura "
                                           "pas quoi corriger. Vous pouvez encore en saisir un.",
                                  messages.WARNING)
            else:
                self.message_user(request, f"{adhesion.libelle} : demande refusée.", messages.SUCCESS)
