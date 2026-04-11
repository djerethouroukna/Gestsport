# Ajouter le webhook secret aux settings
import os

# Lire le fichier settings
settings_path = 'config/settings.py'
with open(settings_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Ajouter le webhook secret si non présent
webhook_secret = "STRIPE_WEBHOOK_SECRET = 'AMadl1WEIkJ1c6DePnBYYa1LIcwvUUUbmCmXPV7d4pk'"

if 'STRIPE_WEBHOOK_SECRET' not in content:
    # Trouver où l'ajouter (après les autres clés Stripe)
    stripe_lines = [i for i, line in enumerate(content.split('\n')) if 'STRIPE_' in line and '=' in line]
    if stripe_lines:
        last_stripe_line = max(stripe_lines)
        lines = content.split('\n')
        lines.insert(last_stripe_line + 1, webhook_secret)
        new_content = '\n'.join(lines)
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ STRIPE_WEBHOOK_SECRET ajouté à config/settings.py")
        print(f"   {webhook_secret}")
    else:
        print("❌ Impossible de trouver où ajouter le webhook secret")
else:
    print("✅ STRIPE_WEBHOOK_SECRET déjà configuré")

print("\n=== INSTRUCTIONS WEBHOOK STRIPE ===")
print("1. Allez sur https://dashboard.stripe.com/webhooks")
print("2. Cliquez sur 'Add endpoint'")
print("3. URL: http://127.0.0.1:8000/payments/stripe/webhook/")
print("4. Secret: AMadl1WEIkJ1c6DePnBYYa1LIcwvUUUbmCmXPV7d4pk")
print("5. Événements:")
print("   - checkout.session.completed")
print("   - payment_intent.succeeded")
print("6. Cliquez sur 'Add endpoint'")
print("\n7. Redémarrez le serveur Django")
