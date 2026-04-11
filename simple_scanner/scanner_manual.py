#!/usr/bin/env python3
# ==============================================================================
# SCANNER GESTSPORT - VERSION MANUELLE PRIORITAIRE
# ==============================================================================

import requests
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
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
API_TOKEN = "952f56a69dd6456297c6363d3f1836892eec9f24"
SCANNER_ID = "scanner_manual_01"
LOCATION = "Entrée Principale"

class ManualScannerApp:
    """Application scanner avec saisie manuelle prioritaire"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Scanner GestSport - Manuel")
        self.root.geometry("600x500")
        self.root.configure(bg='#2c3e50')
        
        # Variables
        self.last_result = None
        self.scan_history = []
        
        # Créer les dossiers
        os.makedirs('logs', exist_ok=True)
        
        # Interface
        self.setup_ui()
        
        # Focus sur le champ de saisie
        self.ticket_entry.focus_set()
        
        logger.info("Demarrage scanner manuel")
    
    def setup_ui(self):
        """Interface utilisateur optimisée pour saisie manuelle"""
        
        # Header
        header = tk.Frame(self.root, bg='#34495e', height=80)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="Scanner GestSport - Manuel", 
                font=("Arial", 18, "bold"),
                bg='#34495e', fg='white').pack(pady=20)
        
        # Zone principale
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Zone de saisie
        input_frame = tk.Frame(main_frame, bg='#2c3e50')
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(input_frame, text="NUMÉRO DU TICKET", 
                font=("Arial", 14, "bold"),
                bg='#2c3e50', fg='white').pack(pady=(0, 10))
        
        # Champ de saisie principal
        self.ticket_entry = tk.Entry(input_frame, 
                                font=("Arial", 16),
                                bg='white', fg='black',
                                insertbackground='black',
                                relief=tk.SOLID,
                                borderwidth=2)
        self.ticket_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Lier la touche Entrée
        self.ticket_entry.bind('<Return>', lambda e: self.scan_ticket())
        self.ticket_entry.bind('<KP_Enter>', lambda e: self.scan_ticket())
        
        # Boutons principaux
        button_frame = tk.Frame(input_frame, bg='#2c3e50')
        button_frame.pack(fill=tk.X)
        
        tk.Button(button_frame, text="🔍 VALIDER", command=self.scan_ticket,
                 font=("Arial", 14, "bold"), bg='#27ae60', fg='white',
                 padx=20, pady=15, width=15).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(button_frame, text="🔄 EFFACER", command=self.clear_entry,
                 font=("Arial", 14), bg='#e74c3c', fg='white',
                 padx=20, pady=15, width=15).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(button_frame, text="📋 HISTORIQUE", command=self.show_history,
                 font=("Arial", 14), bg='#3498db', fg='white',
                 padx=20, pady=15, width=15).pack(side=tk.LEFT)
        
        # Zone de résultat
        result_frame = tk.Frame(main_frame, bg='#2c3e50')
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        tk.Label(result_frame, text="RÉSULTAT DE VALIDATION", 
                font=("Arial", 14, "bold"),
                bg='#2c3e50', fg='white').pack(pady=(0, 10))
        
        # Frame pour le résultat
        self.result_frame_inner = tk.Frame(result_frame, bg='white', relief=tk.SOLID, borderwidth=2)
        self.result_frame_inner.pack(fill=tk.BOTH, expand=True)
        
        self.result_label = tk.Label(self.result_frame_inner, 
                                 text="⏳ En attente de saisie...",
                                 font=("Arial", 16),
                                 bg='white', fg='#666666')
        self.result_label.pack(pady=30)
        
        # Footer
        footer_frame = tk.Frame(self.root, bg='#34495e', height=50)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Label(footer_frame, text=f"Scanner: {SCANNER_ID} | API: {API_BASE_URL}", 
                font=("Arial", 10),
                bg='#34495e', fg='white').pack(pady=15)
    
    def scan_ticket(self):
        """Valide le ticket saisi"""
        ticket_number = self.ticket_entry.get().strip()
        
        if not ticket_number:
            messagebox.showwarning("Attention", "Veuillez entrer un numéro de ticket")
            return
        
        logger.info(f"Saisie manuelle: {ticket_number}")
        
        # Affichage traitement
        self.show_processing("Validation en cours...")
        
        # Validation
        self.validate_ticket(ticket_number)
    
    def clear_entry(self):
        """Efface le champ de saisie"""
        self.ticket_entry.delete(0, tk.END)
        self.ticket_entry.focus_set()
        self.show_result("ATTENTE", "Prêt pour nouvelle saisie", "")
    
    def validate_ticket(self, ticket_number):
        """Valide le ticket via API"""
        try:
            # Vérifier d'abord si le serveur est accessible
            try:
                test_response = requests.get(f"{API_BASE_URL}/tickets/api/scanner/status/", timeout=CONNECTION_CHECK_TIMEOUT)
                if test_response.status_code != 200:
                    raise Exception("Serveur inaccessible")
            except:
                self.show_result("HORS LIGNE", "Serveur inaccessible - Vérifiez la connexion", ticket_number)
                logger.error("Serveur inaccessible")
                return
            
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
            
            self.show_processing("Validation en cours...")
            response = requests.post(url, headers=headers, json=data, timeout=SCAN_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.show_result("VALIDÉ", "Ticket validé avec succès", ticket_number)
                    logger.info(f"Ticket valide: {ticket_number}")
                    self.add_to_history(ticket_number, "VALIDÉ", "Ticket valide")
                    
                    # Enregistrer dans l'audit log
                    scan_details = result.get('ticket', {})
                    self.log_scan_to_audit(ticket_number, "VALIDÉ", scan_details)
                else:
                    message = result.get('message', 'Ticket invalide')
                    error_code = result.get('error_code', None)
                    
                    # Cas spécial pour réservation expirée
                    if error_code == 'EXPIRED_RESERVATION':
                        reservation_date = result.get('reservation_date', None)
                        expiration_time = result.get('expiration_time', None)
                        
                        if reservation_date and expiration_time:
                            message = f"Réservation expirée: {ticket_number}\nDate: {reservation_date}\nHeure d'expiration: {expiration_time}"
                        elif reservation_date:
                            message = f"Réservation expirée: {ticket_number}\nDate: {reservation_date}"
                        else:
                            message = f"Réservation expirée: {ticket_number}"
                        
                        self.show_result("", message, ticket_number)
                        logger.warning(f"Réservation expirée: {ticket_number}")
                        self.add_to_history(ticket_number, "RÉSERVATION EXPIRÉE", message)
                        
                        # Enregistrer dans l'audit log
                        self.log_scan_to_audit(ticket_number, "RÉSERVATION EXPIRÉE", {
                            "error_code": error_code,
                            "reservation_date": reservation_date,
                            "expiration_time": expiration_time
                        })
                    else:
                        # Autres types d'erreurs
                        self.show_result("REJETÉ", message, ticket_number)
                        logger.warning(f"Ticket rejete: {ticket_number}")
                        self.add_to_history(ticket_number, "REJETÉ", message)
                        
                        # Enregistrer dans l'audit log
                        self.log_scan_to_audit(ticket_number, "REJETÉ", {
                            "error_code": error_code,
                            "message": message
                        })
            else:
                # Erreur HTTP 400 ou autre
                try:
                    error_data = response.json()
                    error_code = error_data.get('error_code', None)
                    reservation_date = error_data.get('reservation_date', None)
                    reservation_time = error_data.get('reservation_time', None)
                    reservation_iso = error_data.get('reservation_iso', None)
                    
                    # Gérer les différents types d'erreurs
                    if error_code == 'EXPIRED_RESERVATION':
                        expiration_time = error_data.get('expiration_time', None)
                        expiration_datetime = error_data.get('expiration_datetime', None)
                        
                        if expiration_datetime:
                            message = f"Réservation terminée: {ticket_number}\nExpirée le: {expiration_datetime}"
                        elif expiration_time:
                            message = f"Réservation terminée: {ticket_number}\nExpirée à: {expiration_time}"
                        else:
                            message = f"Réservation terminée: {ticket_number}"
                        
                        self.show_result("TERMINÉE", message, ticket_number)
                        logger.warning(f"Réservation terminée: {ticket_number}")
                        self.add_to_history(ticket_number, "RÉSERVATION TERMINÉE", message)
                        
                        # Enregistrer dans l'audit log
                        self.log_scan_to_audit(ticket_number, "RÉSERVATION TERMINÉE", {
                            "error_code": error_code,
                            "expiration_time": expiration_time,
                            "expiration_datetime": expiration_datetime
                        })
                        
                    elif error_code == 'TICKET_ALREADY_USED':
                        used_at = error_data.get('used_at', None)
                        if used_at:
                            message = f"Ticket déjà utilisé: {ticket_number}\nUtilisé le: {used_at}"
                        else:
                            message = f"Ticket déjà utilisé: {ticket_number}"
                        
                        self.show_result("DÉJÀ UTILISÉ", message, ticket_number)
                        logger.warning(f"Ticket déjà utilisé: {ticket_number}")
                        self.add_to_history(ticket_number, "DÉJÀ UTILISÉ", message)
                        
                        # Enregistrer dans l'audit log
                        self.log_scan_to_audit(ticket_number, "DÉJÀ UTILISÉ", {
                            "error_code": error_code,
                            "used_at": used_at
                        })
                        
                    elif error_code == 'FUTURE_RESERVATION':
                        # Gérer les réservations futures
                        reservation_datetime = error_data.get('reservation_datetime', None)
                        start_time = error_data.get('start_time', None)
                        end_time = error_data.get('end_time', None)
                        
                        if reservation_datetime:
                            message = f"Réservation future: {ticket_number}\nDate: {reservation_datetime}"
                        elif reservation_date and start_time:
                            message = f"Réservation future: {ticket_number}\nDate: {reservation_date}\nDébut: {start_time}"
                        elif reservation_date:
                            message = f"Réservation future: {ticket_number}\nDate: {reservation_date}"
                        else:
                            message = f"Réservation future: {ticket_number}"
                            
                        self.show_result("FUTURE", message, ticket_number)
                        logger.warning(f"Réservation future: {ticket_number}")
                        self.add_to_history(ticket_number, "RÉSERVATION FUTURE", message)
                        
                        # Enregistrer dans l'audit log
                        self.log_scan_to_audit(ticket_number, "RÉSERVATION FUTURE", {
                            "error_code": error_code,
                            "reservation_datetime": reservation_datetime,
                            "start_time": start_time,
                            "end_time": end_time,
                            "reservation_date": reservation_date
                        })
                        
                    else:
                        # Autres types d'erreurs
                        message = error_data.get('message', f'Erreur: {response.status_code}')
                        self.show_result("REJETÉ", message, ticket_number)
                        logger.warning(f"Ticket rejeté: {ticket_number} - {message}")
                        self.add_to_history(ticket_number, "REJETÉ", message)
                        
                        # Enregistrer dans l'audit log
                        self.log_scan_to_audit(ticket_number, "REJETÉ", {
                            "error_code": error_code,
                            "message": message,
                            "status_code": response.status_code
                        })
                        
                except Exception as e:
                    # Erreur de parsing JSON
                    message = f"Erreur serveur: {response.status_code}"
                    self.show_result("ERREUR", message, ticket_number)
                    logger.error(f"Erreur parsing réponse: {ticket_number} - {e}")
                    self.add_to_history(ticket_number, "ERREUR", message)
                    
                    # Enregistrer dans l'audit log
                    self.log_scan_to_audit(ticket_number, "ERREUR", {
                        "error_type": "parsing_error",
                        "status_code": response.status_code,
                        "error_message": str(e)
                    })
                
        except requests.exceptions.ConnectionError:
            self.show_result("HORS LIGNE", "API inaccessible", ticket_number)
            logger.error("API hors ligne")
            self.add_to_history(ticket_number, "HORS LIGNE", "API inaccessible")
            
            # Enregistrer dans l'audit log
            self.log_scan_to_audit(ticket_number, "HORS LIGNE", {
                "error_type": "connection_error",
                "message": "API inaccessible"
            })
        except Exception as e:
            self.show_result("ERREUR", f"Erreur: {str(e)}", ticket_number)
            logger.error(f"Erreur validation: {e}")
            self.add_to_history(ticket_number, "ERREUR", str(e))
            
            # Enregistrer dans l'audit log
            self.log_scan_to_audit(ticket_number, "ERREUR", {
                "error_type": "validation_error",
                "error_message": str(e)
            })
        
        # Vider le champ et remettre le focus
        self.ticket_entry.delete(0, tk.END)
        self.ticket_entry.focus_set()
    
    def log_scan_to_audit(self, ticket_number, scan_result, scan_details):
        """Enregistre le scan dans l'audit log"""
        try:
            url = f"{API_BASE_URL}/audit/api/log/"
            headers = {
                "Authorization": f"Token {API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Préparer les données pour l'audit
            audit_data = {
                "action": "SCAN",
                "model_name": "Ticket",
                "object_repr": f"Ticket {ticket_number}",
                "changes": {
                    "scan_result": scan_result,
                    "scanner_id": SCANNER_ID,
                    "location": LOCATION,
                    "scan_details": scan_details
                },
                "metadata": {
                    "scanner_type": "manual",
                    "ticket_number": ticket_number,
                    "scan_timestamp": datetime.now().isoformat()
                }
            }
            
            # Envoyer à l'API d'audit avec timeout configuré
            audit_response = requests.post(url, headers=headers, json=audit_data, timeout=AUDIT_TIMEOUT)
            
            if audit_response.status_code == 201:
                logger.info(f"Scan enregistré dans audit: {ticket_number} - {scan_result}")
            else:
                logger.warning(f"Erreur enregistrement audit: {audit_response.status_code}")
                
        except Exception as e:
            logger.error(f"Erreur log audit: {e}")
            # Ne pas bloquer le scan si l'audit échoue
    
    def show_processing(self, message):
        """Affiche l'écran de traitement"""
        self.result_frame_inner.configure(bg='#fff3cd')
        self.result_label.configure(text=f"⏳ {message}", fg='#856404')
    
    def show_result(self, statut, message, ticket_number):
        """Affiche le résultat de la validation"""
        self.last_result = {
            'statut': statut,
            'message': message,
            'ticket_number': ticket_number,
            'timestamp': datetime.now().isoformat()
        }
        
        if statut == "VALIDÉ":
            self.result_frame_inner.configure(bg='#d4edda')
            self.result_label.configure(text=f"✅ {statut}: {message}", fg='#155724')
        elif statut == "REJETÉ":
            self.result_frame_inner.configure(bg='#f8d7da')
            self.result_label.configure(text=f"❌ {statut}: {message}", fg='#721c24')
        elif statut == "DÉJÀ UTILISÉ":
            self.result_frame_inner.configure(bg='#fff3cd')
            self.result_label.configure(text=f"⚠️ {statut}: {message}", fg='#856404')
        elif statut == "TERMINÉE":
            self.result_frame_inner.configure(bg='#e2e3e5')
            self.result_label.configure(text=f"⏰ {statut}: {message}", fg='#383d41')
        elif statut == "FUTURE":
            self.result_frame_inner.configure(bg='#cce5ff')
            self.result_label.configure(text=f"🔮 {statut}: {message}", fg='#004085')
        elif statut == "HORS LIGNE":
            self.result_frame_inner.configure(bg='#fff3cd')
            self.result_label.configure(text=f"⚠️ {statut}: {message}", fg='#856404')
        elif statut == "ERREUR":
            self.result_frame_inner.configure(bg='#f8d7da')
            self.result_label.configure(text=f"❌ {statut}: {message}", fg='#721c24')
        else:
            self.result_frame_inner.configure(bg='#f8d7da')
            self.result_label.configure(text=f"⚠️ {statut}: {message}", fg='#721c24')
        
        # Log
        log_entry = f"{datetime.now().isoformat()} | {SCANNER_ID} | {ticket_number} | {statut} | {message}"
        with open("logs/scanner.log", "a", encoding='utf-8') as f:
            f.write(log_entry + "\n")
    
    def add_to_history(self, ticket_number, statut, message):
        """Ajoute à l'historique"""
        self.scan_history.insert(0, {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'ticket': ticket_number,
            'statut': statut,
            'message': message
        })
        
        # Limiter l'historique à 50 entrées
        if len(self.scan_history) > 50:
            self.scan_history = self.scan_history[:50]
    
    def show_history(self):
        """Affiche l'historique des scans"""
        history_window = tk.Toplevel(self.root)
        history_window.title("📋 Historique des Scans")
        history_window.geometry("700x400")
        history_window.configure(bg='#2c3e50')
        
        # Titre
        tk.Label(history_window, text="HISTORIQUE DES SCANS RÉCENTS", 
                font=("Arial", 14, "bold"),
                bg='#2c3e50', fg='white').pack(pady=10)
        
        # Tableau
        columns = ('Heure', 'Ticket', 'Statut', 'Message')
        tree = ttk.Treeview(history_window, columns=columns, show='headings', height=15)
        
        # Configuration des colonnes
        tree.heading('Heure', text='Heure')
        tree.heading('Ticket', text='Numéro Ticket')
        tree.heading('Statut', text='Statut')
        tree.heading('Message', text='Message')
        
        tree.column('Heure', width=80)
        tree.column('Ticket', width=150)
        tree.column('Statut', width=100)
        tree.column('Message', width=350)
        
        # Remplir le tableau
        for entry in self.scan_history:
            tree.insert('', 'end', values=(
                entry['timestamp'],
                entry['ticket'],
                entry['statut'],
                entry['message'][:50] + '...' if len(entry['message']) > 50 else entry['message']
            ))
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Bouton fermer
        tk.Button(history_window, text="Fermer", command=history_window.destroy,
                 font=("Arial", 12), bg='#dc3545', fg='white',
                 padx=20, pady=10).pack(pady=10)

def main():
    """Fonction principale"""
    try:
        os.makedirs('logs', exist_ok=True)
        
        app = ManualScannerApp()
        
        def on_closing():
            if messagebox.askyesno("Quitter", "Voulez-vous vraiment quitter le scanner?"):
                app.root.quit()
                logger.info("Scanner manuel arrete")
        
        app.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        app.root.mainloop()
        
    except Exception as e:
        logger.error(f"Erreur demarrage: {e}")
        messagebox.showerror("Erreur", f"Erreur démarrage: {e}")

if __name__ == "__main__":
    main()
