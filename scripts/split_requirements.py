#!/usr/bin/env python
"""
Script pour séparer les dépendances mobiles des dépendances web
"""
import os
import sys

def split_requirements():
    """Sépare les requirements en web et mobile"""
    
    # Lecture du requirements.txt original
    with open('requirements.txt', 'r') as f:
        all_requirements = f.read().splitlines()
    
    web_requirements = []
    mobile_requirements = []
    
    # Packages mobiles à exclure du déploiement web
    mobile_packages = [
        'kivy',
        'kivymd',
        'kivy-deps',
        'pyqt5',
        'opencv-python',
        'pygame',
        'pil',
        'numpy',  # Partiellement utilisé par mobile
    ]
    
    for req in all_requirements:
        req_lower = req.lower()
        
        # Vérifier si c'est un package mobile
        is_mobile = any(mobile_pkg in req_lower for mobile_pkg in mobile_packages)
        
        if is_mobile:
            mobile_requirements.append(req)
        else:
            web_requirements.append(req)
    
    # Écrire requirements-web.txt
    with open('requirements-web.txt', 'w') as f:
        f.write('\n'.join(web_requirements))
        f.write('\n')
    
    # Écrire requirements-mobile.txt
    with open('requirements-mobile.txt', 'w') as f:
        f.write('\n'.join(mobile_requirements))
        f.write('\n')
    
    print(f"Requirements web: {len(web_requirements)} packages")
    print(f"Requirements mobile: {len(mobile_requirements)} packages")
    print("Fichiers créés: requirements-web.txt, requirements-mobile.txt")

if __name__ == '__main__':
    split_requirements()
