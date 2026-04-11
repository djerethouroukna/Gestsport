#!/usr/bin/env python3
# ==============================================================================
# SCANNER GESTSPORT - VERSION CLAVIER UNIQUEMENT
# ==============================================================================

import requests
import tkinter as tk
from tkinter import messagebox, ttk
import json
import logging
from datetime import datetime
import os
import sys

# Configuration du logging compatible Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scanner.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = "a9dc052f48d8098984e2f916673b51ed2e364929"
SCANNER_ID = "scanner_keyboard_01"
LOCATION = "Entrée Principale"

class KeyboardScannerApp:
    """Application scanner clavier uniquement"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Scanner GestSport - Clavier")
        self.root.geometry("500x400")
        self.root.configure(bg='#2c3e50')
        
        # Variables
        self.current_input = ""
        self.scan_count = 0
        self.valid_count = 0
        
        # Créer les dossiers
        os.makedirs('logs', exist_ok=True)
        
        # Interface
        self.setup_ui()
        
        # Focus sur le champ principal
        self.root.focus_set()
        
        logger.info("Demarrage scanner clavier")
    
    def setup_ui(self):
        """Interface optimisée pour clavier"""
        
        # Header
        header = tk.Frame(self.root, bg='#34495e', height=60)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="🎫 SCANNER CLAVIER", 
                font=("Arial", 16, "bold"),
                bg='#34495e', fg='white').pack(pady=15)
        
        # Zone principale
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Affichage de la saisie
        display_frame = tk.Frame(main_frame, bg='#2c3e50')
        display_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(display_frame, text="NUMÉRO TICKET:", 
                font=("Arial", 12, "bold"),
                bg='#2c3e50', fg='white').pack(anchor='w')
        
        # Champ d'affichage (lecture seule)
        self.display_label = tk.Label(display_frame, 
                                text="",
                                font=("Courier", 18, "bold"),
                                bg='white', fg='black',
                                relief=tk.SUNKEN,
                                borderwidth=2,
                                anchor='w',
                                padx=10, pady=10)
        self.display_label.pack(fill=tk.X, pady=(5, 0))
        
        # Statistiques
        stats_frame = tk.Frame(main_frame, bg='#2c3e50')
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.stats_label = tk.Label(stats_frame, 
                                text="Scans: 0 | Validés: 0 | Rejetés: 0",
                                font=("Arial", 11),
                                bg='#2c3e50', fg='#bdc3c7')
        self.stats_label.pack()
        
        # Zone de résultat
        result_frame = tk.Frame(main_frame, bg='#2c3e50')
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_label = tk.Label(result_frame, 
                                 text="⏳ Prêt à scanner...",
                                 font=("Arial", 14),
                                 bg='#2c3e50', fg='white')
        self.result_label.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(main_frame, 
                             text="Instructions: Tapez le numéro du ticket et appuyez sur ENTRÉE",
                             font=("Arial", 10),
                             bg='#2c3e50', fg='#95a5a6')
        instructions.pack(side=tk.BOTTOM, pady=(10, 0))
        
        # Lier les touches
        self.root.bind('<Key>', self.on_key_press)
        self.root.bind('<Return>', self.validate_current_input)
        self.root.bind('<KP_Enter>', self.validate_current_input)
        self.root.bind('<Escape>', self.clear_input)
        self.root.bind('<BackSpace>', self.on_backspace)
        self.root.bind('<Delete>', self.clear_input)
    
    def on_key_press(self, event):
        """Gère la saisie au clavier"""
        # Ignorer les touches spéciales
        if event.keysym in ['Return', 'KP_Enter', 'Escape', 'BackSpace', 'Delete', 'Tab', 'Shift', 'Control', 'Alt']:
            return
        
        # Ajouter le caractère
        if len(event.char) == 1:  # Caractère imprimable
            self.current_input += event.char
            self.update_display()
    
    def on_backspace(self, event):
        """Gère la touche retour arrière"""
        if self.current_input:
            self.current_input = self.current_input[:-1]
            self.update_display()
    
    def clear_input(self, event=None):
        """Efface la saisie"""
        self.current_input = ""
        self.update_display()
        self.show_result("PRÊT", "Prêt à scanner...")
    
    def update_display(self):
        """Met à jour l'affichage"""
        self.display_label.configure(text=self.current_input)
    
    def validate_current_input(self, event=None):
        """Valide la saisie actuelle"""
        ticket_number = self.current_input.strip()
        
        if not ticket_number:
            self.show_result("ERREUR", "Aucun numéro saisi")
            return
        
        logger.info(f"Saisie clavier: {ticket_number}")
        
        # Validation
        self.validate_ticket(ticket_number)
    
    def validate_ticket(self, ticket_number):
        """Valide le ticket via API"""
        self.scan_count += 1
        
        # Affichage traitement
        self.show_result("TRAITEMENT", "Validation en cours...")
        
        try:
            url = f"{API_BASE_URL}/tickets/api/scanner/scan/"
            headers = {
                "Authorization": f"Token {API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            data = {
                "qr_data": ticket_number,
                "scanner_id": SCANNER_ID,
                "location": LOCATION
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.show_result("VALIDÉ", "✅ Ticket valide", ticket_number)
                    self.valid_count += 1
                    logger.info(f"Ticket valide: {ticket_number}")
                else:
                    message = result.get('message', 'Ticket invalide')
                    self.show_result("REJETÉ", f"❌ {message}", ticket_number)
                    logger.warning(f"Ticket rejete: {ticket_number}")
            else:
                self.show_result("ERREUR", f"⚠️ Réservation trop future: {ticket_number}", ticket_number)
                logger.error(f"Réservation trop future: {ticket_number}")
                
        except requests.exceptions.ConnectionError:
            self.show_result("HORS LIGNE", "🔴 API inaccessible", ticket_number)
            logger.error("API hors ligne")
        except Exception as e:
            self.show_result("ERREUR", f"⚠️ Erreur: {str(e)}", ticket_number)
            logger.error(f"Erreur validation: {e}")
        
        # Mettre à jour les statistiques
        self.update_stats()
        
        # Effacer pour la prochaine saisie
        self.current_input = ""
        self.update_display()
        
        # Remettre le focus
        self.root.focus_set()
    
    def show_result(self, statut, message, ticket_number=""):
        """Affiche le résultat"""
        # Couleurs selon le statut
        colors = {
            "PRÊT": ('#3498db', 'white'),
            "TRAITEMENT": ('#f39c12', 'white'),
            "VALIDÉ": ('#27ae60', 'white'),
            "REJETÉ": ('#e74c3c', 'white'),
            "HORS LIGNE": ('#e67e22', 'white'),
            "ERREUR": ('#95a5a6', 'white')
        }
        
        bg_color, fg_color = colors.get(statut, ('#95a5a6', 'white'))
        
        self.result_label.configure(
            text=message,
            bg=bg_color,
            fg=fg_color,
            relief=tk.RAISED,
            borderwidth=2,
            padx=20,
            pady=15
        )
        
        # Log
        if ticket_number:
            log_entry = f"{datetime.now().isoformat()} | {SCANNER_ID} | {ticket_number} | {statut} | {message}"
            with open("logs/scanner.log", "a", encoding='utf-8') as f:
                f.write(log_entry + "\n")
    
    def update_stats(self):
        """Met à jour les statistiques"""
        rejected = self.scan_count - self.valid_count
        stats_text = f"Scans: {self.scan_count} | Validés: {self.valid_count} | Rejetés: {rejected}"
        self.stats_label.configure(text=stats_text)

def main():
    """Fonction principale"""
    try:
        os.makedirs('logs', exist_ok=True)
        
        app = KeyboardScannerApp()
        
        def on_closing():
            if messagebox.askyesno("Quitter", f"Quitter le scanner?\n\nStatistiques:\nScans: {app.scan_count}\nValidés: {app.valid_count}"):
                app.root.quit()
                logger.info("Scanner clavier arrete")
        
        app.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        app.root.mainloop()
        
    except Exception as e:
        logger.error(f"Erreur demarrage: {e}")
        messagebox.showerror("Erreur", f"Erreur démarrage: {e}")

if __name__ == "__main__":
    main()
