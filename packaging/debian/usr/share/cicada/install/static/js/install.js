document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('install-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingMessage = document.getElementById('loading-message');
    const progressFill = document.getElementById('progress-fill');
    const stepsList = document.getElementById('steps-list');
    const errorMessage = document.getElementById('error-message');
    const successMessage = document.getElementById('success-message');
    const submitBtn = document.getElementById('submit-btn');
    const rgpdConsent = document.getElementById('rgpd_consent');
    const rgpdFields = document.getElementById('rgpd_fields');
    
    // Noms d'affichage pour les étapes
    const stepNames = {
        'db': 'Base de données PostgreSQL',
        'redis': 'Cache Redis',
        'web': 'Application Django',
        'frontend': 'Interface Angular',
        'superuser': 'Création du compte admin',
        'registration': 'Enregistrement de l\'instance'
    };

    // Gérer l'affichage des champs RGPD
    rgpdConsent.addEventListener('change', function(e) {
        if (e.target.checked) {
            rgpdFields.classList.remove('hidden');
            rgpdFields.querySelectorAll('input').forEach(input => {
                input.required = true;
            });
        } else {
            rgpdFields.classList.add('hidden');
            rgpdFields.querySelectorAll('input').forEach(input => {
                input.required = false;
                input.value = '';
            });
        }
    });
    
    // Initialiser l'affichage des champs DB et reverse proxy / Traefik
    toggleDbFields();
    ['db_host', 'db_port', 'db_name', 'db_user'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', schedulePrepareCommand);
    });
    toggleReverseProxyFields();
    toggleFederationFields();
    toggleAcmeEmailMode();
    toggleSmtpFields();
    toggleSmtpAuthFields();

    // Validation du mot de passe
    const password = document.getElementById('admin_password');
    const passwordConfirm = document.getElementById('admin_password_confirm');
    
    function validatePassword() {
        if (password.value !== passwordConfirm.value) {
            passwordConfirm.setCustomValidity('Les mots de passe ne correspondent pas');
        } else {
            passwordConfirm.setCustomValidity('');
        }
    }
    
    password.addEventListener('input', validatePassword);
    passwordConfirm.addEventListener('input', validatePassword);

    // Soumission du formulaire
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Masquer les messages précédents
        errorMessage.classList.add('hidden');
        successMessage.classList.add('hidden');
        
        // Désactiver le formulaire
        form.style.pointerEvents = 'none';
        submitBtn.disabled = true;
        
        // Afficher le loading
        loadingOverlay.classList.remove('hidden');
        updateProgress(0, 'Validation des données...');
        
        // Récupérer les données du formulaire
        const formData = new FormData(form);
        const data = {};
        for (const [key, value] of formData.entries()) {
            if (key === 'rgpd_consent') {
                data[key] = document.getElementById(key).checked;
            } else if (key === 'smtp_enabled' || key === 'smtp_use_auth' || key === 'smtp_use_tls'
                       || key === 'federation_enabled' || key === 'federation_relay') {
                data[key] = document.getElementById(key).checked;
            } else if (key !== 'reverse_proxy_present' && key !== 'acme_email') {
                data[key] = value;
            }
        }
        const reverseProxyPresent = document.getElementById('reverse_proxy_present') && document.getElementById('reverse_proxy_present').checked;
        const useAdminAcmeEmail = document.getElementById('acme_use_admin_email') && document.getElementById('acme_use_admin_email').checked;
        data.use_traefik = !reverseProxyPresent;
        const federationBox = document.getElementById('federation_enabled');
        const relayBox = document.getElementById('federation_relay');
        data.federation_enabled = !!(federationBox && federationBox.checked);
        data.federation_relay = data.federation_enabled && !!(relayBox && relayBox.checked);
        const geonatureRadio = document.getElementById('auth_provider_geonature');
        data.auth_provider = (geonatureRadio && geonatureRadio.checked) ? 'geonature' : 'local';
        if (data.use_traefik) {
            if (useAdminAcmeEmail) {
                data.acme_email = (document.getElementById('admin_email') && document.getElementById('admin_email').value) || '';
            } else {
                data.acme_email = (document.getElementById('acme_email') && document.getElementById('acme_email').value) || '';
            }
        }
        
        try {
            // Envoyer la requête
            const response = await fetch('/api/install', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                updateProgress(100, 'Installation terminée !');
                setTimeout(() => {
                    successMessage.textContent = `Installation réussie ! Redirection vers ${result.redirect_url}...`;
                    successMessage.classList.remove('hidden');
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 2000);
                }, 1000);
            } else {
                throw new Error(result.error || result.errors?.join(', ') || 'Erreur lors de l\'installation');
            }
        } catch (error) {
            loadingOverlay.classList.add('hidden');
            errorMessage.textContent = 'Erreur : ' + error.message;
            errorMessage.classList.remove('hidden');
            form.style.pointerEvents = 'auto';
            submitBtn.disabled = false;
        }
    });

    // Polling du statut pendant l'installation
    let statusInterval;
    
    function startStatusPolling() {
        statusInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/status');
                const status = await response.json();
                
                if (status.status === 'in_progress') {
                    updateProgress(getProgressFromStatus(status.message), status.message);
                    updateStepsList(status.steps || []);
                } else if (status.status === 'completed') {
                    clearInterval(statusInterval);
                    updateProgress(100, status.message);
                    updateStepsList(status.steps || []);
                } else if (status.status === 'failed') {
                    clearInterval(statusInterval);
                    updateStepsList(status.steps || []);
                    throw new Error(status.message);
                }
            } catch (error) {
                // Ignorer les erreurs de polling
            }
        }, 1000);
    }
    
    function updateStepsList(steps) {
        if (!stepsList || steps.length === 0) return;
        
        stepsList.innerHTML = '';
        
        steps.forEach(step => {
            const stepItem = document.createElement('div');
            stepItem.className = `step-item ${step.status || 'pending'}`;
            
            const stepIcon = document.createElement('div');
            stepIcon.className = 'step-icon';
            
            const stepContent = document.createElement('div');
            stepContent.style.flex = '1';
            
            const stepName = document.createElement('div');
            stepName.className = 'step-name';
            stepName.textContent = stepNames[step.name] || step.name;
            
            const stepMessage = document.createElement('div');
            stepMessage.className = 'step-message';
            stepMessage.textContent = step.message || '';
            
            stepContent.appendChild(stepName);
            if (step.message) {
                stepContent.appendChild(stepMessage);
            }
            
            stepItem.appendChild(stepIcon);
            stepItem.appendChild(stepContent);
            stepsList.appendChild(stepItem);
        });
    }
    
    function getProgressFromStatus(message) {
        if (message.includes('Validation')) return 10;
        if (message.includes('Génération')) return 20;
        if (message.includes('Configuration')) return 30;
        if (message.includes('Démarrage')) return 40;
        if (message.includes('Création')) return 60;
        if (message.includes('Enregistrement')) return 80;
        if (message.includes('terminée')) return 100;
        return 50;
    }
    
    function updateProgress(percent, message) {
        progressFill.style.width = percent + '%';
        loadingMessage.textContent = message;
    }
    
    // Démarrer le polling si le formulaire est soumis
    form.addEventListener('submit', startStatusPolling);
});

function toggleReverseProxyFields() {
    const reverseProxyPresent = document.getElementById('reverse_proxy_present');
    const traefikFields = document.getElementById('traefik_fields');
    const reverseProxyFields = document.getElementById('reverse_proxy_fields');
    const acmeEmail = document.getElementById('acme_email');
    if (!reverseProxyPresent || !traefikFields || !reverseProxyFields) return;
    if (reverseProxyPresent.checked) {
        reverseProxyFields.classList.remove('hidden');
        traefikFields.classList.add('hidden');
        if (acmeEmail) { acmeEmail.required = false; acmeEmail.value = ''; }
    } else {
        reverseProxyFields.classList.add('hidden');
        traefikFields.classList.remove('hidden');
        toggleAcmeEmailMode();
    }
}

function toggleAcmeEmailMode() {
    const reverseProxyPresent = document.getElementById('reverse_proxy_present');
    const useAdminEmail = document.getElementById('acme_use_admin_email');
    const acmeEmailGroup = document.getElementById('acme_email_group');
    const acmeEmail = document.getElementById('acme_email');
    if (!useAdminEmail || !acmeEmailGroup || !acmeEmail) return;

    // Sans Traefik, ce champ n'est jamais requis/visible.
    if (reverseProxyPresent && reverseProxyPresent.checked) {
        acmeEmailGroup.classList.add('hidden');
        acmeEmail.required = false;
        acmeEmail.value = '';
        return;
    }

    if (useAdminEmail.checked) {
        acmeEmailGroup.classList.add('hidden');
        acmeEmail.required = false;
        acmeEmail.value = '';
    } else {
        acmeEmailGroup.classList.remove('hidden');
        acmeEmail.required = true;
    }
}

function toggleSmtpFields() {
    const smtpEnabled = document.getElementById('smtp_enabled');
    const smtpFields = document.getElementById('smtp_fields');
    const smtpHost = document.getElementById('smtp_host');
    const smtpPort = document.getElementById('smtp_port');
    const defaultFromEmail = document.getElementById('default_from_email');
    const smtpUseAuth = document.getElementById('smtp_use_auth');
    if (!smtpEnabled || !smtpFields) return;

    if (smtpEnabled.checked) {
        smtpFields.classList.remove('hidden');
        if (smtpHost) smtpHost.required = true;
        if (smtpPort) smtpPort.required = true;
        if (defaultFromEmail) defaultFromEmail.required = true;
    } else {
        smtpFields.classList.add('hidden');
        if (smtpHost) { smtpHost.required = false; smtpHost.value = ''; }
        if (smtpPort) { smtpPort.required = false; smtpPort.value = '587'; }
        if (defaultFromEmail) { defaultFromEmail.required = false; defaultFromEmail.value = ''; }
        if (smtpUseAuth) smtpUseAuth.checked = false;
        toggleSmtpAuthFields();
    }
}

function toggleSmtpAuthFields() {
    const smtpEnabled = document.getElementById('smtp_enabled');
    const smtpUseAuth = document.getElementById('smtp_use_auth');
    const smtpAuthFields = document.getElementById('smtp_auth_fields');
    const smtpUser = document.getElementById('smtp_user');
    const smtpPassword = document.getElementById('smtp_password');
    if (!smtpAuthFields || !smtpUseAuth || !smtpEnabled) return;

    if (smtpEnabled.checked && smtpUseAuth.checked) {
        smtpAuthFields.classList.remove('hidden');
        if (smtpUser) smtpUser.required = true;
        if (smtpPassword) smtpPassword.required = true;
    } else {
        smtpAuthFields.classList.add('hidden');
        if (smtpUser) { smtpUser.required = false; smtpUser.value = ''; }
        if (smtpPassword) { smtpPassword.required = false; smtpPassword.value = ''; }
    }
}

function generatePassword(fieldId) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
    let password = '';
    for (let i = 0; i < 32; i++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    document.getElementById(fieldId).value = password;
}

function togglePasswordVisibility(fieldId, button) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    if (field.type === 'password') {
        field.type = 'text';
        if (button) button.title = 'Masquer';
    } else {
        field.type = 'password';
        if (button) button.title = 'Afficher';
    }
}

function copyFieldValue(fieldId, button) {
    const field = document.getElementById(fieldId);
    if (!field || !field.value) return;

    const copiedLabel = 'Copié';
    const defaultLabel = '&#128203;';

    const onSuccess = () => {
        if (!button) return;
        const original = button.innerHTML;
        button.textContent = copiedLabel;
        setTimeout(() => {
            button.innerHTML = original || defaultLabel;
        }, 1200);
    };

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(field.value).then(onSuccess).catch(() => {
            field.select();
            document.execCommand('copy');
            onSuccess();
            field.setSelectionRange(field.value.length, field.value.length);
        });
    } else {
        field.select();
        document.execCommand('copy');
        onSuccess();
        field.setSelectionRange(field.value.length, field.value.length);
    }
}

function toggleDbFields() {
    const dbType = document.getElementById('db_type').value;
    const dockerFields = document.getElementById('db_docker_fields');
    const existingFields = document.getElementById('db_existing_fields');
    const dbConnectionFields = document.getElementById('db_connection_fields');
    const dbHost = document.getElementById('db_host');
    const dbPort = document.getElementById('db_port');
    const dbNameHelp = document.getElementById('db_name_help');
    const dbUserHelp = document.getElementById('db_user_help');
    const existingSteps = document.getElementById('db_existing_steps');
    const generateBtn = document.querySelector('#db_password ~ .btn-generate');

    if (dbType === 'docker') {
        if (existingSteps) existingSteps.classList.add('hidden');
        if (generateBtn) generateBtn.classList.remove('hidden');
        dockerFields.classList.remove('hidden');
        existingFields.classList.add('hidden');
        if (dbConnectionFields) dbConnectionFields.classList.add('hidden');
        dbHost.value = 'db';
        dbPort.value = '5432';
        dbHost.required = false;
        dbPort.required = false;
        dbHost.readOnly = true;
        dbPort.readOnly = true;
        if (dbNameHelp) dbNameHelp.textContent = 'Sera créée automatiquement si nouvelle instance Docker';
        if (dbUserHelp) dbUserHelp.textContent = 'Sera créé automatiquement si nouvelle instance Docker';
    } else {
        dockerFields.classList.add('hidden');
        existingFields.classList.remove('hidden');
        if (dbConnectionFields) dbConnectionFields.classList.remove('hidden');
        dbHost.required = true;
        dbPort.required = true;
        dbHost.readOnly = false;
        dbPort.readOnly = false;
        if (dbHost.value === 'db') dbHost.value = '';
        if (existingSteps) existingSteps.classList.remove('hidden');
        // Le mot de passe est celui que cicada-prepare-db affiche : en générer un
        // ici ne correspondrait à rien sur le serveur de base.
        if (generateBtn) generateBtn.classList.add('hidden');
        if (dbNameHelp) dbNameHelp.textContent = 'Créée par cicada-prepare-db (option --db-name si autre nom)';
        if (dbUserHelp) dbUserHelp.textContent = 'Créé par cicada-prepare-db (option --db-user si autre nom)';
        updatePrepareCommand();
    }
}

// --- Base existante : commande de préparation et test de connexion ---------

let prepareCommandTimer;
function schedulePrepareCommand() {
    clearTimeout(prepareCommandTimer);
    prepareCommandTimer = setTimeout(updatePrepareCommand, 400);
}

async function updatePrepareCommand() {
    const code = document.getElementById('prepare_db_command');
    const clientSpan = document.getElementById('prepare_db_client');
    const host = document.getElementById('db_host').value.trim();
    if (!code) return;
    if (!host || host === 'db') {
        code.textContent = 'Indiquez d\'abord l\'hôte PostgreSQL ci-dessus.';
        clientSpan.textContent = '—';
        return;
    }
    let clientIp = null;
    let local = false;
    try {
        const r = await fetch('/api/db-client-ip?host=' + encodeURIComponent(host));
        const info = await r.json();
        clientIp = info.client_ip;
        local = info.local;
    } catch (e) { /* réseau : on garde l'adresse de la page */ }
    const options = [];
    const port = document.getElementById('db_port').value.trim();
    const name = document.getElementById('db_name').value.trim();
    const user = document.getElementById('db_user').value.trim();
    if (port && port !== '5432') options.push('--port ' + port);
    if (name && name !== 'cicada') options.push('--db-name ' + name);
    if (user && user !== 'cicada_user') options.push('--db-user ' + user);
    const where = document.getElementById('prepare_db_where');
    const clientLabel = document.getElementById('prepare_db_client_label');
    if (local) {
        // PostgreSQL sur ce serveur : le paquet cicada y a déjà installé le
        // script (et son init.sql), qui autorise les conteneurs Docker.
        where.innerHTML = '<strong>Étape 2</strong> — sur <strong>ce serveur</strong>, lancez :';
        code.textContent = 'sudo cicada-prepare-db --docker-local' + (options.length ? ' ' + options.join(' ') : '');
        clientLabel.textContent = 'les conteneurs de CICADA';
        clientSpan.textContent = clientIp;
        return;
    }
    where.innerHTML = '<strong>Étape 2</strong> — sur le <strong>serveur de base</strong>, en root, lancez :';
    clientLabel.textContent = 'ce serveur';
    // Adresse par laquelle ce serveur joint la base : c'est elle que le serveur
    // de base doit autoriser, et a priori elle par laquelle il nous joint.
    const self = clientIp || window.location.hostname;
    options.unshift('--client ' + (clientIp || '<ip-de-ce-serveur>'));
    code.textContent = 'curl -fsSL http://' + self + ':' + (window.location.port || '4567')
        + '/prepare-db.sh | sudo bash -s -- ' + options.join(' ');
    clientSpan.textContent = clientIp || 'adresse inconnue : vérifiez l\'hôte';
}

async function testDatabase() {
    const list = document.getElementById('test_db_results');
    const btn = document.getElementById('test_db_btn');
    const value = id => document.getElementById(id).value;
    list.innerHTML = '<li class="check-pending">Test en cours…</li>';
    btn.disabled = true;
    try {
        const r = await fetch('/api/test-db', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                db_host: value('db_host'), db_port: value('db_port'), db_name: value('db_name'),
                db_user: value('db_user'), db_password: value('db_password'),
            }),
        });
        const checks = (await r.json()).checks || [];
        list.innerHTML = '';
        checks.forEach(c => {
            const li = document.createElement('li');
            li.className = 'check-' + c.status;
            li.textContent = c.label;
            if (c.detail) {
                const detail = document.createElement('small');
                detail.textContent = c.detail;
                li.appendChild(detail);
            }
            list.appendChild(li);
        });
    } catch (e) {
        list.innerHTML = '<li class="check-error">Test impossible : ' + e.message + '</li>';
    } finally {
        btn.disabled = false;
    }
}

function copyText(elementId, btn) {
    const text = document.getElementById(elementId).textContent;
    const done = () => {
        const old = btn.innerHTML;
        btn.innerHTML = '&#10003;';
        setTimeout(() => { btn.innerHTML = old; }, 1500);
    };
    // navigator.clipboard n'existe qu'en HTTPS ou sur localhost : l'installateur
    // est ouvert en http://<ip>:4567, d'où le repli sur execCommand.
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done);
        return;
    }
    const area = document.createElement('textarea');
    area.value = text;
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    document.execCommand('copy');
    document.body.removeChild(area);
    done();
}

function toggleFederationFields() {
    const enabled = document.getElementById('federation_enabled');
    const fields = document.getElementById('federation_fields');
    const instanceId = document.getElementById('federation_instance_id');
    const instanceLabel = document.getElementById('federation_instance_label');
    const hubUrl = document.getElementById('federation_hub_url');
    const pushToken = document.getElementById('federation_push_token');
    const readToken = document.getElementById('federation_read_token');
    const relay = document.getElementById('federation_relay');
    if (!enabled || !fields) return;

    if (enabled.checked) {
        fields.classList.remove('hidden');
        if (instanceId) instanceId.required = true;
        if (hubUrl) {
            hubUrl.required = true;
            // Décocher vide les champs : recocher rend l'URL du hub RNF.
            if (!hubUrl.value && hubUrl.dataset.default) hubUrl.value = hubUrl.dataset.default;
        }
        if (instanceLabel) instanceLabel.required = true;
        // Jetons facultatifs (#696) : par défaut l'adhésion se demande depuis
        // l'application une fois installée. Le jeton de lecture n'est exigé
        // que si un jeton de dépôt est saisi ET l'exploration relayée.
        if (pushToken) pushToken.required = false;
        if (readToken) readToken.required = !!(relay && relay.checked && pushToken && pushToken.value.trim());
    } else {
        fields.classList.add('hidden');
        [instanceId, instanceLabel, hubUrl, pushToken, readToken].forEach(function (champ) {
            if (champ) { champ.required = false; champ.value = ''; }
        });
        if (relay) relay.checked = false;
    }
}

function toggleGeoNatureAuthFields() {
    // #689 — un seul mode de connexion : les réglages GeoNature ne s'affichent
    // (et ne sont exigés) que si ce mode est choisi. #764 — puis selon la
    // source : base UsersHub ou API GeoNature.
    const enabled = document.getElementById('auth_provider_geonature');
    const fields = document.getElementById('geonature_auth_fields');
    if (!enabled || !fields) return;
    const actif = enabled.checked;
    const parBase = actif && document.getElementById('geonature_auth_source_base').checked;
    const champs = id => document.getElementById(id);
    const api = ['geonature_auth_url', 'geonature_auth_id_application'].map(champs);
    const base = ['usershub_db_host', 'usershub_db_port', 'usershub_db_name', 'usershub_db_user',
                  'usershub_db_password', 'geonature_auth_code_application'].map(champs);

    fields.classList.toggle('hidden', !actif);
    champs('usershub_base_fields').classList.toggle('hidden', !parBase);
    champs('geonature_api_fields').classList.toggle('hidden', !actif || parBase);
    const libelle = champs('geonature_auth_libelle');
    if (libelle) libelle.required = actif;
    api.forEach(c => { if (c) c.required = actif && !parBase; });
    base.forEach(c => { if (c) c.required = parBase; });
    if (!actif) {
        api.concat([champs('geonature_auth_organismes_exclus'), champs('usershub_db_password')])
            .forEach(c => { if (c) c.value = ''; });
    }
}

let usershubCommandTimer;
function scheduleUsersHubCommand() {
    clearTimeout(usershubCommandTimer);
    usershubCommandTimer = setTimeout(updateUsersHubCommand, 400);
}

// #764 — commande de création du compte de lecture, à lancer sur le serveur
// de la base UsersHub (comme cicada-prepare-db pour la base de CICADA).
async function updateUsersHubCommand() {
    const code = document.getElementById('usershub_command');
    const where = document.getElementById('usershub_command_where');
    const clientSpan = document.getElementById('usershub_command_client');
    if (!code) return;
    const value = id => document.getElementById(id).value.trim();
    const host = value('usershub_db_host');
    const base = value('usershub_db_name');
    if (!host || !base) {
        where.textContent = 'Créez le compte de lecture : indiquez d\'abord l\'hôte et la base ci-dessus.';
        code.textContent = '—';
        return;
    }
    let clientIp = null;
    let local = false;
    try {
        const r = await fetch('/api/db-client-ip?host=' + encodeURIComponent(host));
        const info = await r.json();
        clientIp = info.client_ip;
        local = info.local;
    } catch (e) { /* réseau : on garde l'adresse de la page */ }
    const options = ['--db ' + base];
    const port = value('usershub_db_port');
    const role = value('usershub_db_user');
    const app = value('geonature_auth_code_application');
    if (port && port !== '5432') options.push('--port ' + port);
    if (role && role !== 'cicada_usershub') options.push('--role ' + role);
    if (app && app !== 'CICADA') options.push('--code ' + app);
    if (local) {
        where.innerHTML = 'Créez le compte de lecture : sur <strong>ce serveur</strong>, lancez :';
        code.textContent = 'sudo cicada-usershub-lecture --docker-local ' + options.join(' ');
        clientSpan.textContent = 'les conteneurs de CICADA';
        return;
    }
    where.innerHTML = 'Créez le compte de lecture : sur le <strong>serveur de la base UsersHub</strong>, en root, lancez :';
    const self = clientIp || window.location.hostname;
    options.push('--client ' + (clientIp || '<ip-de-ce-serveur>'));
    code.textContent = 'curl -fsSL http://' + self + ':' + (window.location.port || '4567')
        + '/usershub-lecture.sh | sudo bash -s -- ' + options.join(' ');
    clientSpan.textContent = 'ce serveur (' + (clientIp || 'adresse inconnue : vérifiez l\'hôte') + ')';
}

async function testUsersHub() {
    const list = document.getElementById('test_usershub_results');
    const btn = document.getElementById('test_usershub_btn');
    const value = id => document.getElementById(id).value;
    list.innerHTML = '<li class="check-pending">Test en cours…</li>';
    btn.disabled = true;
    try {
        const r = await fetch('/api/test-usershub', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                usershub_db_host: value('usershub_db_host'), usershub_db_port: value('usershub_db_port'),
                usershub_db_name: value('usershub_db_name'), usershub_db_user: value('usershub_db_user'),
                usershub_db_password: value('usershub_db_password'),
                usershub_db_sslmode: value('usershub_db_sslmode'),
                geonature_auth_code_application: value('geonature_auth_code_application'),
            }),
        });
        const checks = (await r.json()).checks || [];
        list.innerHTML = '';
        checks.forEach(c => {
            const li = document.createElement('li');
            li.className = 'check-' + c.status;
            li.textContent = c.label;
            if (c.detail) {
                const detail = document.createElement('small');
                detail.textContent = c.detail;
                li.appendChild(detail);
            }
            list.appendChild(li);
        });
    } catch (e) {
        list.innerHTML = '<li class="check-error">Test impossible : ' + e.message + '</li>';
    } finally {
        btn.disabled = false;
    }
}
