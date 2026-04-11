-- ====================================================================
-- CRÉATION DE L'UTILISATEUR POUR LE SCANNER GESTSPORT
-- ====================================================================
-- Exécutez ce script dans PostgreSQL pour créer l'utilisateur scan_user

-- 1. Créer l'utilisateur scan_user avec le mot de passe
CREATE USER scan_user WITH PASSWORD 'INNOCENT';

-- 2. Donner les permissions de connexion à la base gestsport
GRANT CONNECT ON DATABASE gestsport TO scan_user;

-- 3. Donner les permissions de lecture sur le schéma public
GRANT USAGE ON SCHEMA public TO scan_user;

-- 4. Donner les permissions de lecture sur toutes les tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO scan_user;

-- 5. Donner les permissions de lecture sur toutes les séquences
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO scan_user;

-- 6. Donner les permissions sur les tables spécifiques du scanner
GRANT SELECT ON tickets_ticket TO scan_user;
GRANT SELECT ON reservations_reservation TO scan_user;
GRANT SELECT ON users_user TO scan_user;
GRANT SELECT ON terrains_terrain TO scan_user;
GRANT SELECT ON activities_activity TO scan_user;
GRANT SELECT ON tickets_scan TO scan_user;

-- 7. S'assurer que les futures tables auront aussi les permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO scan_user;

-- 8. Vérification
\du scan_user;

-- Message de confirmation
SELECT 'Utilisateur scan_user créé avec succès!' as message;
