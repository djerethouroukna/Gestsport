// Test simple pour vérifier si JavaScript s'exécute
console.log('=== JAVASCRIPT CHARGE ===');
alert('JavaScript fonctionne !');

// Attendre que la variable soit initialisée (solution au problème de timing)
setTimeout(function() {
    // Debug logs
    console.log('=== INIT DELETE FUNCTIONALITY ===');
    console.log('Is admin user:', window.isAdminUser);
    
    // Si la variable n'est toujours pas correcte, vérifier directement depuis le DOM
    if (!window.isAdminUser) {
        console.log('WARNING: isAdminUser is false, checking for admin indicators...');
        // Vérifier si les boutons admin sont visibles
        const adminButtons = document.querySelectorAll('.btn-delete-terrain');
        if (adminButtons.length > 0) {
            console.log('Admin buttons found, forcing isAdminUser to true');
            window.isAdminUser = true;
        }
    }
    
    console.log('Final isAdminUser after check:', window.isAdminUser);
    
    document.addEventListener('click', function(e) {
        console.log('=== CLICK EVENT ===');
        console.log('Clicked element:', e.target);
        console.log('Element classes:', e.target.className);
        
        const btn = e.target.closest('.btn-delete-terrain');
        if (!btn) {
            console.log('No delete button found');
            return;
        }
        
        console.log('=== DELETE BUTTON FOUND ===');
        console.log('Button element:', btn);
        console.log('Terrain ID:', btn.dataset.id);
        console.log('Terrain name:', btn.dataset.name);
        console.log('Is admin user:', window.isAdminUser);
        
        e.preventDefault();
        
        // Vérifier si l'utilisateur est admin
        if (!window.isAdminUser) {
            console.log('ERROR: User is not admin');
            alert('Seuls les administrateurs peuvent supprimer des terrains');
            return;
        }
        
        // Confirmation de suppression
        if (confirm('Voulez-vous vraiment supprimer le terrain "' + btn.dataset.name + '" ?')) {
            console.log('=== CONFIRMED DELETION ===');
            
            function getCookie(name) {
                const value = '; ' + document.cookie;
                const parts = value.split('; ' + name + '=');
                if (parts.length === 2) return parts.pop().split(';').shift();
            }
            const csrftoken = getCookie('csrftoken');
            console.log('CSRF token:', csrftoken ? 'found' : 'not found');
            
            // Construire l'URL de manière sécurisée
            const terrainId = btn.dataset.id;
            const deleteUrl = '/terrains/' + terrainId + '/delete/';
            console.log('Delete URL:', deleteUrl);
            
            fetch(deleteUrl, {
                method: 'POST',
                headers: { 
                    'X-CSRFToken': csrftoken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            })
            .then(response => {
                console.log('Response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data);
                if (data.success) {
                    alert('Terrain supprimé avec succès !');
                    location.reload();
                } else {
                    console.log('Delete error:', data.error);
                    alert('Erreur: ' + (data.error || 'Erreur inconnue'));
                }
            })
            .catch(error => {
                console.error('Delete error:', error);
                alert('Erreur réseau: ' + error.message);
            });
        } else {
            console.log('Deletion cancelled by user');
        }
    });
}, 100); // Attendre 100ms pour l'initialisation
