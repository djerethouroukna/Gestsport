# Analyse détaillée du problème de visibilité du QR code dans le PDF
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from tickets.services import TicketService
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import json

print("=== ANALYSE DÉTAILLÉE VISIBILITÉ QR CODE ===")

# Récupérer un ticket existant
try:
    ticket = Ticket.objects.first()
    if not ticket:
        print("❌ Aucun ticket trouvé")
        exit()
    
    print(f"Ticket analysé: {ticket.ticket_number}")
    print(f"Réservation: {ticket.reservation.id}")
    print(f"QR code: {ticket.qr_code}")
    
    # 1. Vérifier si le QR code existe dans la base de données
    print(f"\n=== 1. VÉRIFICATION QR CODE BASE DE DONNÉES ===")
    if ticket.qr_code:
        print(f"✅ QR code trouvé: {ticket.qr_code.name}")
        print(f"   Taille: {ticket.qr_code.size} bytes")
        print(f"   Chemin: {ticket.qr_code.path}")
        
        # Vérifier si le fichier existe physiquement
        if os.path.exists(ticket.qr_code.path):
            print(f"✅ Fichier QR code existe sur disque")
            
            # Vérifier la taille du fichier
            file_size = os.path.getsize(ticket.qr_code.path)
            print(f"   Taille fichier: {file_size} bytes")
            
            # Vérifier si l'image est valide
            try:
                img = Image.open(ticket.qr_code.path)
                print(f"✅ Image QR code valide")
                print(f"   Dimensions: {img.size}")
                print(f"   Format: {img.format}")
                print(f"   Mode: {img.mode}")
            except Exception as e:
                print(f"❌ Image QR code invalide: {e}")
        else:
            print(f"❌ Fichier QR code n'existe pas sur disque")
    else:
        print(f"❌ Aucun QR code associé au ticket")
    
    # 2. Analyser le service de génération PDF
    print(f"\n=== 2. ANALYSE SERVICE GÉNÉRATION PDF ===")
    
    # Vérifier les imports dans le service
    try:
        from reportlab.platypus import Image
        print(f"✅ Import ReportLab Image réussi")
    except ImportError as e:
        print(f"❌ Import ReportLab Image échoué: {e}")
    
    # Vérifier les unités
    try:
        from reportlab.lib.units import cm
        print(f"✅ Import unités cm réussi")
        print(f"   6cm = {6*cm} points")
    except ImportError as e:
        print(f"❌ Import unités cm échoué: {e}")
    
    # 3. Créer un QR code personnalisé pour test
    print(f"\n=== 3. CRÉATION QR CODE PERSONNALISÉ POUR TEST ===")
    try:
        # Dimensions
        width, height = 600, 600
        
        # Image de base
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Couleurs
        black = (0, 0, 0)
        gray = (128, 128, 128)
        light_gray = (200, 200, 200)
        blue = (0, 100, 200)
        
        # 1. Cadre extérieur
        border_size = 20
        draw.rectangle([border_size, border_size, width-border_size, height-border_size], outline=black, width=3)
        
        # 2. Cadre intérieur
        inner_border = 40
        draw.rectangle([inner_border, inner_border, width-inner_border, height-inner_border], outline=gray, width=1)
        
        # 3. Zone centrale pour le QR code
        qr_zone_size = 400
        qr_zone_x = (width - qr_zone_size) // 2
        qr_zone_y = (height - qr_zone_size) // 2
        
        # 4. Fond pour la zone QR
        draw.rectangle([qr_zone_x, qr_zone_y, qr_zone_x + qr_zone_size, qr_zone_y + qr_zone_size], 
                     fill='white', outline=light_gray, width=2)
        
        # 5. Intégrer le QR code
        if ticket.qr_code:
            try:
                import qrcode
                
                # Données du ticket
                ticket_data = {
                    'ticket_number': ticket.ticket_number,
                    'terrain_name': ticket.reservation.terrain.name,
                    'date_formatted': ticket.reservation.start_time.strftime('%d/%m/%Y %H:%M'),
                    'duration_minutes': str(ticket.reservation.duration_minutes),
                    'user_name': ticket.reservation.user.get_full_name() or ticket.reservation.user.username,
                    'is_valid': ticket.is_valid
                }
                
                # Générer QR code
                qr = qrcode.QRCode(
                    version=5,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=15,
                    border=2,
                )
                qr.add_data(json.dumps(ticket_data, separators=(',', ':')))
                qr.make(fit=True)
                
                # Créer et redimensionner le QR code
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_size = 300
                qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
                
                # Intégrer le QR code
                qr_x = qr_zone_x + (qr_zone_size - qr_size) // 2
                qr_y = qr_zone_y + (qr_zone_size - qr_size) // 2
                img.paste(qr_img, (qr_x, qr_y))
                
                print(f"✅ QR code intégré dans l'image personnalisée")
                
            except ImportError:
                print(f"❌ qrcode non installé")
        
        # 6. Texte "TICKET"
        try:
            font_large = ImageFont.truetype("arial.ttf", 24)
            font_medium = ImageFont.truetype("arial.ttf", 16)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        
        text = "TICKET"
        try:
            bbox = draw.textbbox((0, 0), text, font=font_large)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text((text_x, 60), text, fill=blue, font=font_large)
        except:
            text_width = len(text) * 12
            text_x = (width - text_width) // 2
            draw.text((text_x, 60), text, fill=blue, font=font_large)
        
        # Sauvegarder pour test
        test_path = f"debug_qr_{ticket.ticket_number}.png"
        img.save(test_path, "PNG", quality=95)
        print(f"✅ QR code personnalisé sauvegardé: {test_path}")
        
        # Vérifier l'image créée
        img_size = os.path.getsize(test_path)
        print(f"   Taille fichier: {img_size} bytes")
        
    except Exception as e:
        print(f"❌ Erreur création QR personnalisé: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Analyser le code du service de génération PDF
    print(f"\n=== 4. ANALYSE CODE SERVICE PDF ===")
    
    # Lire le fichier services.py
    try:
        with open('e:/backend/tickets/services.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier les sections importantes
        if "QR Code personnalisé" in content:
            print(f"✅ Section QR code personnalisé trouvée")
        else:
            print(f"❌ Section QR code personnalisé non trouvée")
        
        if "create_custom_qr_pixel" in content:
            print(f"✅ Fonction create_custom_qr_pixel trouvée")
        else:
            print(f"❌ Fonction create_custom_qr_pixel non trouvée")
        
        if "Image(custom_qr_img" in content:
            print(f"✅ Ajout de l'image QR au PDF trouvé")
        else:
            print(f"❌ Ajout de l'image QR au PDF non trouvé")
        
        # Vérifier les imports
        if "from PIL import Image" in content:
            print(f"✅ Import PIL Image trouvé")
        else:
            print(f"❌ Import PIL Image non trouvé")
        
        if "from reportlab.lib.units import cm" in content:
            print(f"✅ Import unités cm trouvé")
        else:
            print(f"❌ Import unités cm non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur lecture fichier services.py: {e}")
    
    # 5. Générer un PDF de test et analyser
    print(f"\n=== 5. GÉNÉRATION PDF DE TEST ===")
    try:
        pdf_buffer = TicketService.generate_ticket_pdf(ticket)
        pdf_size = len(pdf_buffer.getvalue())
        print(f"✅ PDF généré: {pdf_size} bytes")
        
        # Sauvegarder le PDF
        with open(f"debug_ticket_{ticket.ticket_number}.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        print(f"✅ PDF sauvegardé: debug_ticket_{ticket.ticket_number}.pdf")
        
        # Analyse de la taille
        if pdf_size < 10000:
            print(f"⚠️ PDF très petit, probablement sans QR code")
        elif pdf_size < 20000:
            print(f"⚠️ PDF petit, QR code peut-être absent")
        else:
            print(f"✅ PDF de taille normale, QR code probablement inclus")
            
    except Exception as e:
        print(f"❌ Erreur génération PDF: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Résumé des problèmes possibles
    print(f"\n=== 6. RÉSUMÉ DES PROBLÈMES POSSIBLES ===")
    
    problems = []
    
    # Vérifier si le QR code existe
    if not ticket.qr_code:
        problems.append("❌ Aucun QR code associé au ticket")
    
    # Vérifier si le fichier existe
    if ticket.qr_code and not os.path.exists(ticket.qr_code.path):
        problems.append("❌ Fichier QR code n'existe pas sur disque")
    
    # Vérifier la taille du PDF
    if 'pdf_size' in locals() and pdf_size < 20000:
        problems.append("❌ PDF trop petit, QR code probablement absent")
    
    # Vérifier les imports
    try:
        from reportlab.lib.units import cm
    except ImportError:
        problems.append("❌ Import unités cm manquant")
    
    try:
        from PIL import Image
    except ImportError:
        problems.append("❌ Import PIL Image manquant")
    
    if problems:
        print(f"Problèmes identifiés:")
        for problem in problems:
            print(f"  {problem}")
    else:
        print(f"✅ Aucun problème évident détecté")
    
    print(f"\n=== SOLUTIONS POSSIBLES ===")
    print(f"1. Vérifier que le QR code est bien généré pour tous les tickets")
    print(f"2. S'assurer que les imports sont corrects dans services.py")
    print(f"3. Vérifier que la fonction create_custom_qr_pixel est accessible")
    print(f"4. S'assurer que l'image QR est bien ajoutée au PDF")
    print(f"5. Vérifier les dimensions et les unités (6*cm = 170 points)")
    
except Exception as e:
    print(f"❌ Erreur générale: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== CONCLUSION ===")
print(f"L'analyse détaillée a été effectuée pour identifier les causes possibles")
print(f"du problème de visibilité du QR code dans le PDF généré.")
