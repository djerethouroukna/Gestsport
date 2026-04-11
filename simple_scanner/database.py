# ==============================================================================
# CONNEXION ET VÉRIFICATION BASE DE DONNÉES POSTGRESQL
# ==============================================================================

import psycopg2
import psycopg2.extras
from datetime import datetime
from config import get_database_config
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de la connexion à la base PostgreSQL"""
    
    def __init__(self):
        self.config = get_database_config()
        self.connection = None
    
    def connect(self):
        """Établit la connexion à la base de données"""
        try:
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                sslmode=self.config.get('sslmode', 'prefer')
            )
            logger.info("✅ Connexion base de données établie")
            return True
        except psycopg2.Error as e:
            logger.error(f"❌ Erreur connexion base: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion à la base de données"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Connexion base de données fermée")
    
    def execute_query(self, query, params=None):
        """Exécute une requête SQL et retourne les résultats"""
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                    return result
                else:
                    self.connection.commit()
                    return cursor.rowcount
        except psycopg2.Error as e:
            logger.error(f"❌ Erreur requête SQL: {e}")
            return None
    
    def verifier_ticket(self, ticket_number):
        """Vérifie si un ticket existe et retourne ses informations"""
        query = """
            SELECT 
                t.id as ticket_id,
                t.ticket_number,
                t.is_used,
                t.used_at,
                t.created_at as ticket_created,
                r.start_time as reservation_start,
                r.end_time as reservation_end,
                r.status as reservation_status,
                r.total_amount,
                u.first_name,
                u.last_name,
                u.email,
                tr.name as terrain_name,
                a.title as activity_title
            FROM tickets_ticket t
            JOIN reservations_reservation r ON t.reservation_id = r.id
            JOIN users_user u ON r.user_id = u.id
            JOIN terrains_terrain tr ON r.terrain_id = tr.id
            LEFT JOIN activities_activity a ON r.activity_id = a.id
            WHERE t.ticket_number = %s
        """
        
        result = self.execute_query(query, (ticket_number,))
        
        if result and len(result) > 0:
            ticket_info = result[0]
            logger.info(f"✅ Ticket trouvé: {ticket_number}")
            return {
                'trouve': True,
                'donnees': ticket_info
            }
        else:
            logger.warning(f"⚠️ Ticket non trouvé: {ticket_number}")
            return {
                'trouve': False,
                'message': 'Ticket non trouvé dans la base'
            }
    
    def valider_regles_ticket(self, ticket_info):
        """Applique les règles de validation locales"""
        now = datetime.now()
        validations = []
        
        # Règle 1: Ticket déjà utilisé
        if ticket_info['is_used']:
            validations.append({
                'code': 'TICKET_DEJA_UTILISE',
                'message': 'Ticket déjà utilisé',
                'valide': False
            })
        
        # Règle 2: Réservation future
        elif ticket_info['reservation_start'] > now:
            validations.append({
                'code': 'RESERVATION_FUTURE',
                'message': 'Réservation future',
                'valide': False,
                'details': f"Validé à partir du {ticket_info['reservation_start'].strftime('%d/%m/%Y %H:%M')}"
            })
        
        # Règle 3: Réservation expirée
        elif ticket_info['reservation_end'] < now:
            validations.append({
                'code': 'RESERVATION_EXPIREE',
                'message': 'Réservation expirée',
                'valide': False,
                'details': f"Expirée le {ticket_info['reservation_end'].strftime('%d/%m/%Y %H:%M')}"
            })
        
        # Règle 4: Réservation non confirmée
        elif ticket_info['reservation_status'] != 'confirmed':
            validations.append({
                'code': 'RESERVATION_NON_CONFIRMEE',
                'message': 'Réservation non confirmée',
                'valide': False
            })
        
        # Règle 5: Ticket valide
        else:
            validations.append({
                'code': 'TICKET_VALIDE',
                'message': 'Ticket valide',
                'valide': True
            })
        
        return validations
    
    def logger_scan(self, ticket_number, resultat, scanner_id, api_response=None):
        """Enregistre un scan dans les logs"""
        timestamp = datetime.now().isoformat()
        
        # Créer la table des logs si elle n'existe pas
        create_table_query = """
            CREATE TABLE IF NOT EXISTS scan_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                scanner_id VARCHAR(50),
                ticket_number VARCHAR(50),
                resultat VARCHAR(20),
                message TEXT,
                api_response JSONB
            )
        """
        self.execute_query(create_table_query)
        
        # Insérer le log
        insert_query = """
            INSERT INTO scan_logs (timestamp, scanner_id, ticket_number, resultat, message, api_response)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        self.execute_query(insert_query, (timestamp, scanner_id, ticket_number, resultat, api_response))
        
        logger.info(f"📝 Scan loggé: {ticket_number} -> {resultat}")
    
    def get_scan_history(self, scanner_id, limit=50):
        """Récupère l'historique des scans pour un scanner"""
        query = """
            SELECT timestamp, ticket_number, resultat, message
            FROM scan_logs
            WHERE scanner_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        return self.execute_query(query, (scanner_id, limit))
    
    def get_statistics(self, scanner_id):
        """Retourne les statistiques pour un scanner"""
        stats_query = """
            SELECT 
                COUNT(*) as total_scans,
                COUNT(CASE WHEN resultat = 'VALIDÉ' THEN 1 END) as scans_valides,
                COUNT(CASE WHEN resultat = 'REJETÉ' THEN 1 END) as scans_rejetes,
                MAX(timestamp) as dernier_scan
            FROM scan_logs
            WHERE scanner_id = %s
                AND timestamp >= CURRENT_DATE
        """
        
        return self.execute_query(stats_query, (scanner_id,))
    
    def test_connexion(self):
        """Teste la connexion à la base de données"""
        try:
            if self.connect():
                # Test simple
                result = self.execute_query("SELECT 1 as test")
                self.disconnect()
                return {
                    'success': True,
                    'message': 'Connexion base de données réussie'
                }
            else:
                return {
                    'success': False,
                    'message': 'Échec connexion base de données'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur test connexion: {str(e)}'
            }

# ==============================================================================
# FONCTIONS GLOBALES SIMPLIFIÉES
# ==============================================================================

# Instance globale du gestionnaire de base
db_manager = DatabaseManager()

def verifier_ticket(ticket_number):
    """Fonction simplifiée pour vérifier un ticket"""
    return db_manager.verifier_ticket(ticket_number)

def valider_regles_ticket(ticket_info):
    """Fonction simplifiée pour valider les règles"""
    return db_manager.valider_regles_ticket(ticket_info)

def logger_scan(ticket_number, resultat, scanner_id, api_response=None):
    """Fonction simplifiée pour logger un scan"""
    return db_manager.logger_scan(ticket_number, resultat, scanner_id, api_response)

def get_scan_history(scanner_id, limit=50):
    """Fonction simplifiée pour l'historique"""
    return db_manager.get_scan_history(scanner_id, limit)

def get_statistics(scanner_id):
    """Fonction simplifiée pour les statistiques"""
    return db_manager.get_statistics(scanner_id)

def test_connexion_base():
    """Fonction simplifiée pour tester la connexion"""
    return db_manager.test_connexion()

if __name__ == "__main__":
    # Test de connexion au démarrage
    print("=== TEST CONNEXION BASE DE DONNÉES ===")
    test_result = test_connexion_base()
    
    if test_result['success']:
        print(f"✅ {test_result['message']}")
        
        # Test de vérification d'un ticket
        print("\n=== TEST VÉRIFICATION TICKET ===")
        ticket_test = verifier_ticket("TKT-TEST123")
        if ticket_test['trouve']:
            print(f"✅ Test ticket trouvé: {ticket_test['donnees']['ticket_number']}")
            regles = valider_regles_ticket(ticket_test['donnees'])
            for regle in regles:
                statut = "✅" if regle['valide'] else "❌"
                print(f"{statut} {regle['code']}: {regle['message']}")
        else:
            print(f"❌ Test ticket non trouvé")
    else:
        print(f"❌ {test_result['message']}")
    
    print("\n=== PRÊT POUR LE SCANNER ===")
