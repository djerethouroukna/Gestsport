#!/usr/bin/env python
import os
import django

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from terrains.models import Terrain

def main():
    print("=== Vérification des terrains dans la base de données ===")
    
    # Compter les terrains
    count = Terrain.objects.count()
    print(f"Nombre total de terrains: {count}")
    
    if count > 0:
        print("\nListe des terrains:")
        for terrain in Terrain.objects.all():
            print(f"- ID: {terrain.id}")
            print(f"  Nom: {terrain.name}")
            print(f"  Type: {terrain.terrain_type}")
            print(f"  Statut: {terrain.status}")
            print(f"  Capacité: {terrain.capacity}")
            print(f"  Prix/h: {terrain.price_per_hour}")
            print("---")
    else:
        print("\n⚠️  Aucun terrain trouvé dans la base de données!")
        print("Création de terrains de test...")
        
        # Créer quelques terrains de test
        test_terrains = [
            {
                'name': 'Stade Mahamat Ouya',
                'description': 'Principal stade de N\'Djamena',
                'terrain_type': 'football',
                'capacity': 2000,
                'price_per_hour': 500.00,
                'status': 'available'
            },
            {
                'name': 'Terrain de Tennis Centre',
                'description': 'Terrain de tennis professionnel',
                'terrain_type': 'tennis',
                'capacity': 4,
                'price_per_hour': 75.00,
                'status': 'available'
            },
            {
                'name': 'Terrain Multisports Farcha',
                'description': 'Terrain pour basketball et volleyball',
                'terrain_type': 'basketball',
                'capacity': 50,
                'price_per_hour': 100.00,
                'status': 'maintenance'
            }
        ]
        
        for terrain_data in test_terrains:
            terrain = Terrain.objects.create(**terrain_data)
            print(f"✅ Créé: {terrain.name}")
        
        print(f"\n✅ {len(test_terrains)} terrains de test créés avec succès!")

if __name__ == '__main__':
    main()
