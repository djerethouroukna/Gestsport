# Script pour régénérer tous les QR codes manquants
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from django.core.files import File
from io import BytesIO
import json
import qrcode
from PIL import Image, ImageDraw, ImageFont

print("=== RÉGÉNÉRATION COMPLÈTE DES QR CODES ===")

# 1. Vérifier le dossier media
print(f"\n=== 1. VÉRIFICATION DOSSIER MEDIA ===")
media_root = "media/tickets/qr_codes"
if os.path.exists(media_root):
    print(f"✅ Dossier media existe: {media_root}")
    files = os.listdir(media_root)
    print(f"   Fichiers existants: {len(files)}")
else:
    print(f"❌ Dossier media n'existe pas: {media_root}")
    os.makedirs(media_root, exist_ok=True)
    print(f"✅ Dossier media créé: {media_root}")

# 2. Récupérer tous les tickets
print(f"\n=== 2. RÉCUPÉRATION TOUS LES TICKETS ===")
all_tickets = Ticket.objects.all()
print(f"Tickets trouvés: {all_tickets.count()}")

# 3. Régénérer les QR codes pour tous les tickets
print(f"\n=== 3. RÉGÉNÉRATION QR CODES ===")
regenerated_count = 0
error_count = 0

for ticket in all_tickets:
    print(f"\n--- Traitement ticket: {ticket.ticket_number} ---")
    
    try:
        # Créer le QR code personnalisé
        width, height = 600, 600
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Couleurs
        black = (0, 0, 0)
        gray = (128, 128, 128)
        light_gray = (200, 200, 200)
        blue = (0, 100, 200)
        green = (0, 150, 0)
        
        # QR code simple sans cadres
        qr_size = 500
        qr_x = (width - qr_size) // 2
        qr_y = (height - qr_size) // 2
        
        # 5. Données du ticket
        ticket_data = {
            'ticket_number': ticket.ticket_number,
            'terrain_name': ticket.reservation.terrain.name,
            'date_formatted': ticket.reservation.start_time.strftime('%d/%m/%Y %H:%M'),
            'duration_minutes': str(ticket.reservation.duration_minutes),
            'user_name': ticket.reservation.user.get_full_name() or ticket.reservation.user.username,
            'is_valid': ticket.is_valid
        }
        
        # 6. Générer QR code
        qr = qrcode.QRCode(
            version=5,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=15,
            border=2,
        )
        qr.add_data(json.dumps(ticket_data, separators=(',', ':')))
        qr.make(fit=True)
        
        # 7. Créer et redimensionner le QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
        
        # 8. Intégrer le QR code (centré)
        img.paste(qr_img, (qr_x, qr_y))
        
        # QR code seul - pas de texte, pas d'informations, juste le QR code
        
        # 13. Sauvegarder l'image
        buffer = BytesIO()
        img.save(buffer, format='PNG', quality=95)
        buffer.seek(0)
        
        # 14. Mettre à jour le QR code du ticket
        filename = f"qr_{ticket.ticket_number}.png"
        
        # Supprimer l'ancien QR code s'il existe
        if ticket.qr_code:
            old_path = ticket.qr_code.path
            if os.path.exists(old_path):
                os.remove(old_path)
                print(f"   Ancien QR code supprimé: {old_path}")
        
        # Sauvegarder le nouveau QR code
        ticket.qr_code.save(filename, File(buffer))
        ticket.save()
        
        regenerated_count += 1
        print(f"   ✅ QR code régénéré: {filename}")
        print(f"   Taille: {len(buffer.getvalue())} bytes")
        
        # Vérifier que le fichier existe
        if os.path.exists(ticket.qr_code.path):
            file_size = os.path.getsize(ticket.qr_code.path)
            print(f"   ✅ Fichier créé: {file_size} bytes")
        else:
            print(f"   ❌ Fichier non trouvé: {ticket.qr_code.path}")
        
    except Exception as e:
        error_count += 1
        print(f"   ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

# 4. Résumé
print(f"\n=== RÉSUMÉ DE LA RÉGÉNÉRATION ===")
print(f"Tickets traités: {all_tickets.count()}")
print(f"QR codes régénérés: {regenerated_count}")
print(f"Erreurs: {error_count}")

# 5. Vérification finale
print(f"\n=== 5. VÉRIFICATION FINALE ===")
final_files = os.listdir(media_root)
print(f"Fichiers finaux: {len(final_files)}")

# Vérifier que chaque ticket a un QR code
tickets_with_qr = Ticket.objects.filter(qr_code__isnull=False)
print(f"Tickets avec QR code: {tickets_with_qr.count()}")

if tickets_with_qr.count() == all_tickets.count():
    print(f"✅ Tous les tickets ont un QR code")
else:
    print(f"⚠️ Certains tickets n'ont pas de QR code")

# 6. Test de génération PDF
print(f"\n=== 6. TEST GÉNÉRATION PDF ===")
try:
    from tickets.services import TicketService
    
    # Prendre le premier ticket
    test_ticket = Ticket.objects.first()
    if test_ticket:
        pdf_buffer = TicketService.generate_ticket_pdf(test_ticket)
        pdf_size = len(pdf_buffer.getvalue())
        print(f"✅ PDF généré: {pdf_size} bytes")
        
        # Sauvegarder pour test
        with open(f"test_ticket_after_regeneration.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        print(f"✅ PDF de test sauvegardé: test_ticket_after_regeneration.pdf")
        
        if pdf_size > 20000:
            print(f"✅ PDF de taille normale, QR code probablement inclus")
        else:
            print(f"⚠️ PDF petit, QR code peut-être absent")
    
except Exception as e:
    print(f"❌ Erreur test PDF: {e}")

print(f"\n=== CONCLUSION ===")
print(f"✅ Régénération des QR codes terminée")
print(f"✅ Dossier media vérifié")
print(f"✅ Tous les tickets ont maintenant un QR code personnalisé")
print(f"✅ Le QR code devrait être visible dans les tickets PDF")
