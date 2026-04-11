#!/usr/bin/env python3
# ==============================================================================
# APPLICATION PRINCIPALE DU SCANNER GESTSPORT
# ==============================================================================

import cv2
import numpy as np
import requests
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
import json
import logging
from datetime import datetime
import os

# Importation des modules locaux
from config import get_api_config, get_retry_config, get_camera_config
from database import verifier_ticket, valider_regles_ticket, logger_scan

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScannerApp:
    """Application principale du scanner GestSport"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Scanner GestSport")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2c3e50')
        
        # Variables d'état
        self.camera = None
        self.scanning = False
        self.last_result = None
        self.api_config = get_api_config()
        self.retry_config = get_retry_config()
        self.api_status = "unknown"  # Statut API pour le thread principal
        
        # Créer les dossiers nécessaires
        os.makedirs('logs', exist_ok=True)
        
        # Initialiser l'interface
        self.setup_ui()
        self.setup_camera()
        
        # Démarrer la détection automatique
        self.start_scanning()
        
        # Démarrer la mise à jour du statut API
        self.update_api_status()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        
        # Frame principale
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(main_frame)
        
        # Zone de scan
        self.create_scan_area(main_frame)
        
        # Zone de résultat
        self.create_result_area(main_frame)
        
        # Zone de contrôle
        self.create_control_area(main_frame)
        
        # Footer
        self.create_footer(main_frame)
    
    def create_header(self, parent):
        """Crée l'en-tête de l'application"""
        header_frame = tk.Frame(parent, bg='#34495e', height=80)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Logo et titre
        title_frame = tk.Frame(header_frame, bg='#34495e')
        title_frame.pack(side=tk.LEFT, padx=20, pady=20)
        
        tk.Label(title_frame, text="🎯", font=("Arial", 24), 
                bg='#34495e', fg='white').pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(title_frame, text="Scanner GestSport", font=("Arial", 18, "bold"),
                bg='#34495e', fg='white').pack(side=tk.LEFT)
        
        # Statut connexion
        status_frame = tk.Frame(header_frame, bg='#34495e')
        status_frame.pack(side=tk.RIGHT, padx=20, pady=20)
        
        self.connection_status = tk.Label(status_frame, text="⚪ Test...", 
                                      font=("Arial", 12), bg='#34495e', fg='#f39c12')
        self.connection_status.pack()
        
        # Test de connexion API
        threading.Thread(target=self.test_api_connection, daemon=True).start()
    
    def create_scan_area(self, parent):
        """Crée la zone de scan avec caméra"""
        scan_frame = tk.Frame(parent, bg='#2c3e50', relief=tk.RIDGE, borderwidth=2)
        scan_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Titre de la zone
        tk.Label(scan_frame, text="📷 ZONE DE SCAN", font=("Arial", 14, "bold"),
                bg='#2c3e50', fg='white').pack(pady=10)
        
        # Frame pour la caméra
        camera_frame = tk.Frame(scan_frame, bg='black', relief=tk.SUNKEN, borderwidth=2)
        camera_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.camera_label = tk.Label(camera_frame, bg='black')
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instructions = tk.Label(scan_frame, text="Positionnez un QR code devant la caméra",
                           font=("Arial", 11), bg='#2c3e50', fg='#bdc3c7')
        instructions.pack(pady=5)
    
    def create_result_area(self, parent):
        """Crée la zone d'affichage des résultats"""
        result_frame = tk.Frame(parent, bg='#2c3e50', relief=tk.RIDGE, borderwidth=2)
        result_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Titre
        tk.Label(result_frame, text="📊 RÉSULTAT DE VALIDATION",
                font=("Arial", 14, "bold"), bg='#2c3e50', fg='white').pack(pady=10)
        
        # Frame pour le résultat
        self.result_frame_inner = tk.Frame(result_frame, bg='white', height=200)
        self.result_frame_inner.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.result_label = tk.Label(self.result_frame_inner, text="⏳ En attente de scan...",
                                 font=("Arial", 16), bg='white', fg='#666666')
        self.result_label.pack(pady=30)
        
        # Détails du ticket (cachés par défaut)
        self.ticket_details_frame = tk.Frame(self.result_frame_inner, bg='white')
        
        self.ticket_number_label = tk.Label(self.ticket_details_frame, text="", 
                                        font=("Arial", 12, "bold"), bg='white')
        self.ticket_user_label = tk.Label(self.ticket_details_frame, text="", 
                                      font=("Arial", 11), bg='white')
        self.ticket_terrain_label = tk.Label(self.ticket_details_frame, text="", 
                                         font=("Arial", 11), bg='white')
        self.ticket_time_label = tk.Label(self.ticket_details_frame, text="", 
                                      font=("Arial", 11), bg='white')
    
    def create_control_area(self, parent):
        """Crée la zone de contrôle"""
        control_frame = tk.Frame(parent, bg='#2c3e50')
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Boutons principaux
        button_frame = tk.Frame(control_frame, bg='#2c3e50')
        button_frame.pack()
        
        # Bouton scan manuel
        tk.Button(button_frame, text="🔍 Scan Manuel", command=self.manual_scan,
                 font=("Arial", 12), bg='#3498db', fg='white',
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        # Bouton historique
        tk.Button(button_frame, text="📋 Historique", command=self.show_history,
                 font=("Arial", 12), bg='#28a745', fg='white',
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        # Bouton paramètres
        tk.Button(button_frame, text="⚙️ Paramètres", command=self.show_settings,
                 font=("Arial", 12), bg='#ffc107', fg='black',
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        # Bouton quitter
        tk.Button(button_frame, text="❌ Quitter", command=self.quit_app,
                 font=("Arial", 12), bg='#dc3545', fg='white',
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
    
    def create_footer(self, parent):
        """Crée le pied de page"""
        footer_frame = tk.Frame(parent, bg='#34495e', height=50)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Informations système
        info_text = f"Scanner: {self.api_config['scanner_id']} | API: {self.api_config['base_url']}"
        tk.Label(footer_frame, text=info_text, font=("Arial", 10),
                bg='#34495e', fg='white').pack(pady=15)
    
    def setup_camera(self):
        """Configure et démarre la caméra"""
        try:
            self.camera = cv2.VideoCapture(0)
            camera_config = get_camera_config()
            
            if self.camera.isOpened():
                # Configuration de la caméra
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config['resolution'][0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config['resolution'][1])
                self.camera.set(cv2.CAP_PROP_FPS, camera_config['fps'])
                
                logger.info("✅ Caméra initialisée")
                self.update_camera_preview()
            else:
                logger.error("❌ Impossible d'ouvrir la caméra")
                messagebox.showerror("Erreur", "Impossible d'initialiser la caméra")
        except Exception as e:
            logger.error(f"❌ Erreur caméra: {e}")
            messagebox.showerror("Erreur", f"Erreur caméra: {e}")
    
    def update_camera_preview(self):
        """Met à jour la preview de la caméra"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # Redimensionner pour l'affichage
                frame = cv2.resize(frame, (640, 480))
                
                # Convertir pour Tkinter
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                photo = ImageTk.PhotoImage(image=image)
                
                self.camera_label.configure(image=photo)
        
        # Planifier la prochaine mise à jour
        if self.scanning:
            self.root.after(30, self.update_camera_preview)
    
    def start_scanning(self):
        """Démarre la détection automatique de QR codes"""
        self.scanning = True
        threading.Thread(target=self.scan_qr_codes, daemon=True).start()
    
    def stop_scanning(self):
        """Arrête la détection de QR codes"""
        self.scanning = False
    
    def scan_qr_codes(self):
        """Détecte et traite les QR codes en continu"""
        while self.scanning:
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if not ret:
                    continue
                
                # Conversion en niveaux de gris
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Détection des QR codes
                decoded_objects = decode(gray)
                
                for obj in decoded_objects:
                    try:
                        qr_data = obj.data.decode('utf-8')
                        self.root.after(0, self.process_qr_result, qr_data)
                        time.sleep(2)  # Pause pour éviter validations multiples
                    except Exception as e:
                        logger.error(f"❌ Erreur décodage QR: {e}")
                
                time.sleep(0.1)  # Pause pour éviter surcharge CPU
    
    def process_qr_result(self, qr_data):
        """Traite le résultat d'un QR code détecté"""
        logger.info(f"🎫 QR Code détecté: {qr_data}")
        
        # Affichage du traitement
        self.show_processing("Validation en cours...")
        
        # Validation en arrière-plan
        threading.Thread(target=self.validate_ticket, args=(qr_data,), daemon=True).start()
    
    def validate_ticket(self, ticket_number):
        """Valide un ticket via base locale et API"""
        try:
            # Étape 1: Vérification base locale
            ticket_result = verifier_ticket(ticket_number)
            
            if not ticket_result['trouve']:
                self.show_result("REJETÉ", "Ticket non trouvé", ticket_number)
                logger_scan(ticket_number, "REJETÉ", self.api_config['scanner_id'])
                return
            
            ticket_info = ticket_result['donnees']
            
            # Étape 2: Validation des règles locales
            validations = valider_regles_ticket(ticket_info)
            validation_result = validations[0]  # Prendre la première validation
            
            if not validation_result['valide']:
                self.show_result("REJETÉ", validation_result['message'], ticket_number, ticket_info)
                logger_scan(ticket_number, "REJETÉ", self.api_config['scanner_id'], 
                          json.dumps({'local_validation': validation_result}))
                return
            
            # Étape 3: Validation API distante
            api_result = self.validate_ticket_api(ticket_number)
            
            if api_result and api_result.get('success'):
                # Succès API
                self.show_result("VALIDÉ", "Ticket validé avec succès", ticket_number, ticket_info)
                logger_scan(ticket_number, "VALIDÉ", self.api_config['scanner_id'], json.dumps(api_result))
            else:
                # Erreur API
                error_msg = api_result.get('message', f'Réservation trop future: {ticket_number}') if api_result else f'Réservation trop future: {ticket_number}'
                self.show_result("ERREUR", error_msg, ticket_number, ticket_info)
                logger_scan(ticket_number, "ERREUR_API", self.api_config['scanner_id'], json.dumps(api_result))
                
        except Exception as e:
            logger.error(f"❌ Erreur validation ticket: {e}")
            self.show_result("ERREUR", f"Erreur traitement: {str(e)}", ticket_number)
    
    def validate_ticket_api(self, ticket_number):
        """Valide le ticket via l'API distante"""
        url = f"{self.api_config['base_url']}/tickets/api/scanner/scan/"
        headers = {
            "Authorization": f"Token {self.api_config['token']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "qr_data": ticket_number,
            "scanner_id": self.api_config['scanner_id'],
            "location": self.api_config.get('location', 'Scanner Principal')
        }
        
        # Tentatives avec retry
        for attempt in range(self.retry_config['max_attempts']):
            try:
                response = requests.post(url, headers=headers, json=data, 
                                      timeout=self.api_config['timeout'])
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"⚠️ Tentative {attempt + 1} échouée: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Tentative {attempt + 1} erreur: {e}")
            
            if attempt < self.retry_config['max_attempts'] - 1:
                time.sleep(self.retry_config['delay'] / 1000)
        
        return None
    
    def show_processing(self, message):
        """Affiche l'écran de traitement"""
        self.result_frame_inner.configure(bg='#fff3cd')
        self.result_label.configure(text=f"⏳ {message}", fg='#856404')
        
        # Cacher les détails du ticket
        for widget in self.ticket_details_frame.winfo_children():
            widget.pack_forget()
    
    def show_result(self, statut, message, ticket_number, ticket_info=None):
        """Affiche le résultat de la validation"""
        self.last_result = {
            'statut': statut,
            'message': message,
            'ticket_number': ticket_number,
            'timestamp': datetime.now().isoformat()
        }
        
        if statut == "VALIDÉ":
            # Succès - fond vert
            self.result_frame_inner.configure(bg='#d4edda')
            self.result_label.configure(text=f"✅ {statut}", fg='#155724')
            
            # Afficher les détails du ticket
            if ticket_info:
                self.show_ticket_details(ticket_info)
                
        else:
            # Erreur - fond rouge
            self.result_frame_inner.configure(bg='#f8d7da')
            self.result_label.configure(text=f"❌ {statut}", fg='#721c24')
            
            # Cacher les détails du ticket
            for widget in self.ticket_details_frame.winfo_children():
                widget.pack_forget()
            
            # Afficher le message d'erreur
            error_label = tk.Label(self.ticket_details_frame, text=f"🔍 {message}",
                                font=("Arial", 12), bg='#f8d7da', fg='#721c24')
            error_label.pack(pady=20)
    
    def show_ticket_details(self, ticket_info):
        """Affiche les détails du ticket validé"""
        # Vider le frame
        for widget in self.ticket_details_frame.winfo_children():
            widget.pack_forget()
        
        # Afficher les informations
        tk.Label(self.ticket_details_frame, text=f"🎫 Numéro: {ticket_info['ticket_number']}",
                font=("Arial", 12, "bold"), bg='white', fg='black').pack(pady=2)
        
        user_name = f"{ticket_info['first_name']} {ticket_info['last_name']}".strip()
        tk.Label(self.ticket_details_frame, text=f"👤 Utilisateur: {user_name}",
                font=("Arial", 11), bg='white', fg='black').pack(pady=2)
        
        tk.Label(self.ticket_details_frame, text=f"🏟️ Terrain: {ticket_info['terrain_name']}",
                font=("Arial", 11), bg='white', fg='black').pack(pady=2)
        
        activity = ticket_info.get('activity_title', 'Réservation standard')
        tk.Label(self.ticket_details_frame, text=f"⚽ Activité: {activity}",
                font=("Arial", 11), bg='white', fg='black').pack(pady=2)
        
        # Formatter les dates
        start_time = ticket_info['reservation_start']
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        tk.Label(self.ticket_details_frame, text=f"📅 Début: {start_time.strftime('%d/%m/%Y %H:%M')}",
                font=("Arial", 11), bg='white', fg='black').pack(pady=2)
        
        tk.Label(self.ticket_details_frame, text=f"✅ Validé: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                font=("Arial", 11, "bold"), bg='white', fg='#155724').pack(pady=5)
        
        self.ticket_details_frame.pack(pady=10)
    
    def manual_scan(self):
        """Ouvre la fenêtre de scan manuel"""
        ticket_number = simpledialog.askstring("Scan Manuel", 
                                            "Entrez le numéro du ticket:",
                                            parent=self.root)
        if ticket_number:
            self.process_qr_result(ticket_number.strip())
    
    def show_history(self):
        """Affiche l'historique des scans"""
        history_window = tk.Toplevel(self.root)
        history_window.title("📋 Historique des Scans")
        history_window.geometry("800x600")
        history_window.configure(bg='#2c3e50')
        
        # Créer un tableau pour l'historique
        columns = ('Timestamp', 'Ticket', 'Résultat', 'Message')
        tree = ttk.Treeview(history_window, columns=columns, show='headings', height=20)
        
        # Configuration des colonnes
        tree.heading('Timestamp', text='Date/Heure')
        tree.heading('Ticket', text='Numéro Ticket')
        tree.heading('Résultat', text='Résultat')
        tree.heading('Message', text='Message')
        
        tree.column('Timestamp', width=150)
        tree.column('Ticket', width=150)
        tree.column('Résultat', width=100)
        tree.column('Message', width=300)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Charger l'historique
        try:
            from database import get_scan_history
            history = get_scan_history(self.api_config['scanner_id'], limit=100)
            
            if history:
                for record in history:
                    tree.insert('', 'end', values=(
                        record['timestamp'],
                        record['ticket_number'],
                        record['resultat'],
                        record['message']
                    ))
        except Exception as e:
            logger.error(f"❌ Erreur chargement historique: {e}")
        
        # Bouton fermer
        tk.Button(history_window, text="Fermer", command=history_window.destroy,
                 font=("Arial", 12), bg='#dc3545', fg='white',
                 padx=20, pady=10).pack(pady=10)
    
    def show_settings(self):
        """Affiche la fenêtre des paramètres"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("⚙️ Paramètres du Scanner")
        settings_window.geometry("600x400")
        settings_window.configure(bg='#2c3e50')
        
        # Afficher les paramètres actuels
        params_frame = tk.Frame(settings_window, bg='#2c3e50')
        params_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Paramètres API
        tk.Label(params_frame, text="PARAMÈTRES API", font=("Arial", 14, "bold"),
                bg='#2c3e50', fg='white').pack(pady=(0, 10))
        
        tk.Label(params_frame, text=f"URL API: {self.api_config['base_url']}",
                font=("Arial", 11), bg='#2c3e50', fg='white').pack(anchor='w')
        tk.Label(params_frame, text=f"Scanner ID: {self.api_config['scanner_id']}",
                font=("Arial", 11), bg='#2c3e50', fg='white').pack(anchor='w')
        tk.Label(params_frame, text=f"Location: {self.api_config.get('location', 'Non défini')}",
                font=("Arial", 11), bg='#2c3e50', fg='white').pack(anchor='w')
        
        # Paramètres système
        tk.Label(params_frame, text="PARAMÈTRES SYSTÈME", font=("Arial", 14, "bold"),
                bg='#2c3e50', fg='white').pack(pady=(20, 10))
        
        tk.Label(params_frame, text=f"Version: 1.0.0",
                font=("Arial", 11), bg='#2c3e50', fg='white').pack(anchor='w')
        tk.Label(params_frame, text=f"Logs: logs/scanner.log",
                font=("Arial", 11), bg='#2c3e50', fg='white').pack(anchor='w')
        
        # Bouton fermer
        tk.Button(settings_window, text="Fermer", command=settings_window.destroy,
                 font=("Arial", 12), bg='#dc3545', fg='white',
                 padx=20, pady=10).pack(pady=20)
    
    def test_api_connection(self):
        """Teste la connexion à l'API en arrière-plan"""
        try:
            url = f"{self.api_config['base_url']}/tickets/api/scanner/status/"
            headers = {"Authorization": f"Token {self.api_config['token']}"}
            params = {"scanner_id": self.api_config['scanner_id']}
            
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                logger.info("Connexion API etablie")
                # Stocker le statut pour le thread principal
                self.api_status = "online"
            else:
                logger.warning(f"Réservation trop future: Erreur API {response.status_code}")
                self.api_status = "error"
                
        except Exception as e:
            logger.error(f"Erreur connexion API: {e}")
            self.api_status = "offline"
    
    def update_api_status(self):
        """Met à jour le statut API depuis le thread principal"""
        try:
            if hasattr(self, 'api_status'):
                if self.api_status == "online":
                    self.connection_status.configure(text="🟢 En ligne", fg='#28a745')
                elif self.api_status == "error":
                    self.connection_status.configure(text="🔴 Réservation trop future", fg='#dc3545')
                elif self.api_status == "offline":
                    self.connection_status.configure(text="🔴 Hors ligne", fg='#dc3545')
                else:
                    self.connection_status.configure(text="⚪ Test...", fg='#f39c12')
            
            # Planifier la prochaine mise à jour
            self.root.after(5000, self.update_api_status)  # Toutes les 5 secondes
        except:
            pass
    
    def quit_app(self):
        """Quitte l'application proprement"""
        if messagebox.askyesno("Quitter", "Voulez-vous vraiment quitter le scanner?"):
            self.stop_scanning()
            if self.camera:
                self.camera.release()
            self.root.quit()
            logger.info("Application scanner arrete")

def main():
    """Fonction principale de l'application"""
    try:
        # Créer le dossier logs s'il n'existe pas
        os.makedirs('logs', exist_ok=True)
        
        # Créer et lancer l'application
        app = ScannerApp()
        
        # Gérer la fermeture propre
        def on_closing():
            app.quit_app()
        
        app.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Démarrer la boucle principale
        logger.info("Demarrage du scanner GestSport")
        app.root.mainloop()
        
    except Exception as e:
        logger.error(f"Erreur demarrage application: {e}")
        messagebox.showerror("Erreur", f"Erreur démarrage: {e}")

if __name__ == "__main__":
    main()
