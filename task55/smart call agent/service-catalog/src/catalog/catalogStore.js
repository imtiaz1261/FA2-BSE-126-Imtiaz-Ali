const { Pool } = require('pg');
const config = require('../config/env');
const { validateServiceEntry, SEED_SERVICES } = require('./schema');

const pool = new Pool({ connectionString: config.DATABASE_URL });

function rowToEntry(row) {
  return {
    service_id: row.service_id,
    name: row.name,
    description: row.description,
    required_documents: row.required_documents,
    avg_duration_minutes: row.avg_duration_minutes,
    eligible_locations: row.eligible_locations,
    example_phrases: row.example_phrases,
    active: row.active,
  };
}

async function listServices({ activeOnly = true } = {}) {
  const query = activeOnly
    ? 'SELECT * FROM services WHERE active = true ORDER BY name'
    : 'SELECT * FROM services ORDER BY name';
  const { rows } = await pool.query(query);
  return rows.map(rowToEntry);
}

async function getServiceById(serviceId) {
  const { rows } = await pool.query('SELECT * FROM services WHERE service_id = $1', [serviceId]);
  return rows[0] ? rowToEntry(rows[0]) : null;
}

async function upsertService(entry) {
  const { valid, errors } = validateServiceEntry(entry);
  if (!valid) throw new Error(`Invalid service entry: ${errors.join(', ')}`);

  await pool.query(
    `INSERT INTO services (service_id, name, description, required_documents, avg_duration_minutes, eligible_locations, example_phrases, active, updated_at)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
     ON CONFLICT (service_id) DO UPDATE SET
       name = EXCLUDED.name,
       description = EXCLUDED.description,
       required_documents = EXCLUDED.required_documents,
       avg_duration_minutes = EXCLUDED.avg_duration_minutes,
       eligible_locations = EXCLUDED.eligible_locations,
       example_phrases = EXCLUDED.example_phrases,
       active = EXCLUDED.active,
       updated_at = now()`,
    [
      entry.service_id,
      entry.name,
      entry.description,
      entry.required_documents,
      entry.avg_duration_minutes,
      entry.eligible_locations,
      entry.example_phrases || [],
      entry.active !== false,
    ]
  );
}

async function seedIfEmpty() {
  const { rows } = await pool.query('SELECT COUNT(*)::int AS count FROM services');
  if (rows[0].count > 0) return { seeded: false };

  for (const entry of SEED_SERVICES) {
    await upsertService(entry);
  }
  return { seeded: true, count: SEED_SERVICES.length };
}

module.exports = { pool, listServices, getServiceById, upsertService, seedIfEmpty };
