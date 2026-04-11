#!/usr/bin/env python3
# ==============================================================================
# VERSION STABLE DU SCANNER GESTSPORT (SANS THREADING ISSUES)
# ==============================================================================

import cv2
import numpy as np
import requests
import time
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
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

# Configuration simple
API_BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = "952f56a69dd6456297c6363d3f1836892eec9f24"
SCANNER_ID = "scanner_stable_01"
LOCATION = "Entrée Principale"

class StableScannerApp:
    """Application stable du scanner sans threading issues"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Scanner GestSport - Stable")
        self.root.geometry("800x600")
        self.root.configure(bg='#2c3e50')
        
        # Variables
        self.camera = None
        self.scanning = False
        self.last_result = None
        self.api_status = "unknown"
        self.last_qr_data = None
        self.last_scan_time = 0
        
        # Créer les dossiers
        os.makedirs('logs', exist_ok=True)
        
        # Interface
        self.setup_ui()
        self.setup_camera()
        
        # Démarrer le scan
        self.start_scanning()
        
        # Démarrer la mise à jour du statut
        self.update_status()
    
    def setup_ui(self):
        """Interface utilisateur"""
        
        # Header
        header = tk.Frame(self.root, bg='#34495e', height=80)
        header.pack(fill=tk.X)
        
        # Titre
        title_frame = tk.Frame(header, bg='#34495e')
        title_frame.pack(side=tk.LEFT, padx=20, pady=20)
        
        tk.Label(title_frame, text="Scanner GestSport", font=("Arial", 18, "bold"),
                bg='#34495e', fg='white').pack(side=tk.LEFT)
        
        # Statut
        status_frame = tk.Frame(header, bg='#34495e')
        status_frame.pack(side=tk.RIGHT, padx=20, pady=20)
        
        self.connection_status = tk.Label(status_frame, text="⚪ Test...", 
                                      font=("Arial", 12), bg='#34495e', fg='#f39c12')
        self.connection_status.pack()
        
        # Zone de scan
        scan_frame = tk.Frame(self.root, bg='#2c3e50')
        scan_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(scan_frame, text="ZONE DE SCAN", font=("Arial", 14, "bold"),
                bg='#2c3e50', fg='white').pack(pady=10)
        
        # Caméra
        self.camera_label = tk.Label(scan_frame, bg='black', width=640, height=480)
        self.camera_label.pack(pady=10)
        
        tk.Label(scan_frame, text="Positionnez un QR code devant la camera",
                font=("Arial", 11), bg='#2c3e50', fg='#bdc3c7').pack(pady=5)
        
        # Zone résultat
        self.result_frame = tk.Frame(self.root, bg='#2c3e50')
        self.result_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.result_label = tk.Label(self.result_frame, text="En attente de scan...",
                                   font=("Arial", 16), bg='#2c3e50', fg='white')
        self.result_label.pack(pady=10)
        
        # Boutons
        button_frame = tk.Frame(self.root, bg='#2c3e50')
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Manuel", command=self.manual_scan,
                 font=("Arial", 12), bg='#3498db', fg='white',
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Test API", command=self.test_api_sync,
                 font=("Arial", 12), bg='#28a745', fg='white',
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Quitter", command=self.quit_app,
                 font=("Arial", 12), bg='#dc3545', fg='white',
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
    
    def setup_camera(self):
        """Configure la caméra"""
        try:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                logger.info("Camera initialisee")
                self.update_camera_preview()
            else:
                logger.error("Impossible d'ouvrir la camera")
                messagebox.showerror("Erreur", "Impossible d'initialiser la camera")
        except Exception as e:
            logger.error(f"Erreur camera: {e}")
            messagebox.showerror("Erreur", f"Erreur camera: {e}")
    
    def update_camera_preview(self):
        """Met à jour la preview caméra (thread principal)"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # Redimensionner
                frame = cv2.resize(frame, (640, 480))
                
                # Détecter les QR codes (dans le thread principal)
                self.detect_qr_codes(frame)
                
                # Convertir pour Tkinter
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                photo = ImageTk.PhotoImage(image=image)
                
                self.camera_label.configure(image=photo)
        
        # Planifier la prochaine mise à jour
        if self.scanning:
            self.root.after(30, self.update_camera_preview)
    
    def detect_qr_codes(self, frame):
        """Détecte les QR codes (thread principal)"""
        try:
            # Conversion en niveaux de gris
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Détection QR codes
            decoded_objects = decode(gray)
            
            for obj in decoded_objects:
                try:
                    qr_data = obj.data.decode('utf-8')
                    
                    # Éviter les scans multiples
                    current_time = time.time()
                    if (qr_data != self.last_qr_data or 
                        current_time - self.last_scan_time > 3):
                        
                        self.last_qr_data = qr_data
                        self.last_scan_time = current_time
                        self.process_qr_result(qr_data)
                        
                except Exception as e:
                    logger.error(f"Erreur decodage QR: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur detection QR: {e}")
    
    def start_scanning(self):
        """Démarre la détection QR code"""
        self.scanning = True
    
    def stop_scanning(self):
        """Arrête la détection"""
        self.scanning = False
    
    def process_qr_result(self, qr_data):
        """Traite le résultat QR code"""
        logger.info(f"QR Code detecte: {qr_data}")
        
        # Affichage traitement
        self.result_label.configure(text="Validation en cours...", fg='#f39c12')
        
        # Validation synchrone (pas de threading)
        self.validate_ticket(qr_data)
    
    def validate_ticket(self, ticket_number):
        """Valide le ticket via API (synchrone)"""
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
                    self.show_result("VALIDE", "Ticket valide avec succes", ticket_number)
                    logger.info(f"Ticket valide: {ticket_number}")
                else:
                    self.show_result("REJETE", result.get('message', 'Ticket invalide'), ticket_number)
                    logger.warning(f"Ticket rejete: {ticket_number}")
            else:
                self.show_result("ERREUR", f"Réservation trop future: {ticket_number}", ticket_number)
                logger.error(f"Réservation trop future: {ticket_number}")
                
        except requests.exceptions.ConnectionError:
            self.show_result("HORS LIGNE", "API inaccessible", ticket_number)
            logger.error("API hors ligne")
        except Exception as e:
            self.show_result("ERREUR", f"Erreur: {str(e)}", ticket_number)
            logger.error(f"Erreur validation: {e}")
    
    def show_result(self, statut, message, ticket_number):
        """Affiche le résultat"""
        self.last_result = {
            'statut': statut,
            'message': message,
            'ticket_number': ticket_number,
            'timestamp': datetime.now().isoformat()
        }
        
        if statut == "VALIDE":
            self.result_label.configure(text=f"OK {statut}: {message}", fg='#27ae60')
        elif statut == "REJETE":
            self.result_label.configure(text=f"KO {statut}: {message}", fg='#e74c3c')
        elif statut == "HORS LIGNE":
            self.result_label.configure(text=f"OFF {statut}: {message}", fg='#e67e22')
        else:
            self.result_label.configure(text=f"ERR {statut}: {message}", fg='#f39c12')
        
        # Log
        log_entry = f"{datetime.now().isoformat()} | {SCANNER_ID} | {ticket_number} | {statut} | {message}"
        with open("logs/scanner.log", "a", encoding='utf-8') as f:
            f.write(log_entry + "\n")
    
    def manual_scan(self):
        """Scan manuel"""
        ticket_number = simpledialog.askstring("Scan Manuel", "Entrez le numero du ticket:")
        if ticket_number:
            self.process_qr_result(ticket_number.strip())
    
    def test_api_sync(self):
        """Test API synchrone"""
        try:
            url = f"{API_BASE_URL}/tickets/api/scanner/status/"
            headers = {"Authorization": f"Token {API_TOKEN}"}
            params = {"scanner_id": SCANNER_ID}
            
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                self.api_status = "online"
                logger.info("Connexion API etablie")
            else:
                self.api_status = "error"
                logger.warning(f"Erreur API: {response.status_code}")
                
        except Exception as e:
            self.api_status = "offline"
            logger.error(f"Erreur connexion API: {e}")
    
    def update_status(self):
        """Met à jour le statut API (thread principal)"""
        try:
            if self.api_status == "online":
                self.connection_status.configure(text="🟢 En ligne", fg='#28a745')
            elif self.api_status == "error":
                self.connection_status.configure(text="🔴 Erreur API", fg='#dc3545')
            elif self.api_status == "offline":
                self.connection_status.configure(text="🔴 Hors ligne", fg='#dc3545')
            else:
                self.connection_status.configure(text="⚪ Test...", fg='#f39c12')
            
            # Planifier la prochaine mise à jour
            self.root.after(5000, self.update_status)
        except:
            pass
    
    def quit_app(self):
        """Quitte l'application"""
        if messagebox.askyesno("Quitter", "Voulez-vous vraiment quitter?"):
            self.stop_scanning()
            if self.camera:
                self.camera.release()
            self.root.quit()
            logger.info("Scanner arrete")

def main():
    """Fonction principale"""
    try:
        os.makedirs('logs', exist_ok=True)
        
        app = StableScannerApp()
        
        def on_closing():
            app.quit_app()
        
        app.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        logger.info("Demarrage scanner stable")
        app.root.mainloop()
        
    except Exception as e:
        logger.error(f"Erreur demarrage: {e}")
        messagebox.showerror("Erreur", f"Erreur demarrage: {e}")

if __name__ == "__main__":
    main()
