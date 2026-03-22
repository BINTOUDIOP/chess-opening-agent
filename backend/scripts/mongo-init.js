// Projet : FFE Chess Agent - Proof of Concept
// Auteur : Bintou DIOP


// Initialisation MongoDB : FFE Chess Agent
db = db.getSiblingDB('ffe_chess');

// Collection : sessions de jeu
db.createCollection('sessions');
db.sessions.createIndex({ created_at: -1 });

// Collection : historique des parties
db.createCollection('games');
db.games.createIndex({ session_id: 1, played_at: -1 });

// Collection : cache des réponses agent (évite les appels redondants)
db.createCollection('agent_cache');
db.agent_cache.createIndex({ fen: 1 }, { unique: true });
db.agent_cache.createIndex({ cached_at: 1 }, { expireAfterSeconds: 3600 }); // TTL 1h

print('✅ Collections MongoDB initialisées : sessions, games, agent_cache');
