# Test format mois français
import datetime

# Test 1: Format strftime avec locale
try:
    from datetime import datetime
    import locale
    
    # Définir la locale française
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    
    # Tester le format
    date_test = datetime(2025, 3, 1)
    format_result = date_test.strftime('%B %Y')
    print(f"Test strftime avec locale: {format_result}")
    
    # Test 2: Format manuel
    mois_noms = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    print(f"Liste des mois manuelle: {mois_noms}")
    
    # Vérifier si le format fonctionne
    for i, mois in enumerate(mois_noms, 1):
        date_test = datetime(2025, i, 1)
        format_test = date_test.strftime('%B %Y')
        print(f"Mois {i}: {mois} -> {format_test}")
        
    print("Test terminé")
    
except Exception as e:
    print(f"Erreur: {e}")
