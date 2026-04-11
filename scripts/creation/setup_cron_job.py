# setup_cron_job.py - Script pour configurer le cron job
import os
import sys
from django.core.management import execute_from_command_line

# Configuration du cron job pour les réservations expirées
CRON_COMMAND = """
# Ajouter à crontab avec: crontab -e
# Exécuter tous les jours à minuit
0 0 * * * /usr/bin/python3 /chemin/vers/votre/projet/manage.py check_expired_reservations >> /var/log/reservations.log 2>&1

# Ou pour Windows (utilisateur Task Scheduler)
# Créer une tâche planifiée qui exécute :
# python /chemin/vers/votre/projet/manage.py check_expired_reservations
"""

def setup_cron():
    """Configure le cron job pour la vérification des réservations expirées"""
    print("🔧 Configuration du cron job pour les réservations expirées")
    print("\n📋 Instructions pour Linux/Mac:")
    print("1. Ouvrir le crontab: crontab -e")
    print("2. Ajouter la ligne suivante:")
    print("0 0 * * * /usr/bin/python3 " + os.path.abspath("manage.py") + " check_expired_reservations >> /var/log/reservations.log 2>&1")
    print("3. Sauvegarder et quitter")
    
    print("\n📋 Instructions pour Windows:")
    print("1. Ouvrir le Planificateur de tâches")
    print("2. Créer une nouvelle tâche")
    print("3. Déclencheur: Quotidien à 00:00")
    print("4. Action: Démarrer un programme")
    print("5. Programme: python " + os.path.abspath("manage.py"))
    print("6. Arguments: check_expired_reservations")
    
    print("\n🧪 Test du cron job:")
    try:
        execute_from_command_line(['manage.py', 'check_expired_reservations'])
        print("✅ Test réussi !")
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")

if __name__ == '__main__':
    setup_cron()
