# ──────────────────────────────────────────────────────────────────────────────
# ListingAI — Terraform Outputs
# ──────────────────────────────────────────────────────────────────────────────

# ── Droplet ──────────────────────────────────────────────────────────────────

output "droplet_ip" {
  description = "Public IPv4 address of the application Droplet"
  value       = digitalocean_droplet.app.ipv4_address
}

output "droplet_private_ip" {
  description = "Private (VPC) IPv4 address of the application Droplet"
  value       = digitalocean_droplet.app.ipv4_address_private
}

output "ssh_command" {
  description = "SSH command to connect to the Droplet"
  value       = "ssh deploy@${digitalocean_droplet.app.ipv4_address}"
}

# ── PostgreSQL ───────────────────────────────────────────────────────────────

output "postgres_host_private" {
  description = "Private hostname for the managed PostgreSQL cluster"
  value       = digitalocean_database_cluster.postgres.private_host
}

output "postgres_port" {
  description = "PostgreSQL port"
  value       = digitalocean_database_cluster.postgres.port
}

output "postgres_user" {
  description = "PostgreSQL application user"
  value       = digitalocean_database_user.listingai.name
}

output "postgres_password" {
  description = "PostgreSQL application user password"
  value       = digitalocean_database_user.listingai.password
  sensitive   = true
}

output "postgres_database" {
  description = "PostgreSQL database name"
  value       = digitalocean_database_db.listingai.name
}

output "database_url" {
  description = "Async DATABASE_URL for the backend (asyncpg, private network)"
  value       = "postgresql+asyncpg://${digitalocean_database_user.listingai.name}:${digitalocean_database_user.listingai.password}@${digitalocean_database_cluster.postgres.private_host}:${digitalocean_database_cluster.postgres.port}/${digitalocean_database_db.listingai.name}?sslmode=require"
  sensitive   = true
}

output "database_url_sync" {
  description = "Sync DATABASE_URL_SYNC for Alembic migrations (psycopg2, private network)"
  value       = "postgresql://${digitalocean_database_user.listingai.name}:${digitalocean_database_user.listingai.password}@${digitalocean_database_cluster.postgres.private_host}:${digitalocean_database_cluster.postgres.port}/${digitalocean_database_db.listingai.name}?sslmode=require"
  sensitive   = true
}

output "pool_connection_uri" {
  description = "Connection pool URI (transaction mode, private network)"
  value       = digitalocean_database_connection_pool.listingai.private_uri
  sensitive   = true
}

# ── Redis ────────────────────────────────────────────────────────────────────

output "redis_host_private" {
  description = "Private hostname for the managed Redis cluster"
  value       = digitalocean_database_cluster.redis.private_host
}

output "redis_port" {
  description = "Redis port"
  value       = digitalocean_database_cluster.redis.port
}

output "redis_password" {
  description = "Redis password"
  value       = digitalocean_database_cluster.redis.password
  sensitive   = true
}

output "redis_url" {
  description = "REDIS_URL for the backend (private network, TLS)"
  value       = "rediss://:${digitalocean_database_cluster.redis.password}@${digitalocean_database_cluster.redis.private_host}:${digitalocean_database_cluster.redis.port}/0"
  sensitive   = true
}

output "celery_broker_url" {
  description = "CELERY_BROKER_URL for Celery workers (private network, TLS, db 1)"
  value       = "rediss://:${digitalocean_database_cluster.redis.password}@${digitalocean_database_cluster.redis.private_host}:${digitalocean_database_cluster.redis.port}/1"
  sensitive   = true
}

# ── Spaces (S3) ──────────────────────────────────────────────────────────────

output "spaces_endpoint" {
  description = "Spaces S3-compatible endpoint URL"
  value       = "https://${var.spaces_region}.digitaloceanspaces.com"
}

output "spaces_bucket_name" {
  description = "Spaces bucket name"
  value       = digitalocean_spaces_bucket.media.name
}

output "spaces_bucket_domain" {
  description = "Spaces bucket domain (for direct access)"
  value       = digitalocean_spaces_bucket.media.bucket_domain_name
}

output "spaces_cdn_domain" {
  description = "CDN domain for the Spaces bucket"
  value       = digitalocean_cdn.media.endpoint
}

output "spaces_access_key" {
  description = "Spaces access key (pass-through from variable)"
  value       = var.spaces_access_key
  sensitive   = true
}

output "spaces_secret_key" {
  description = "Spaces secret key (pass-through from variable)"
  value       = var.spaces_secret_key
  sensitive   = true
}

output "spaces_region" {
  description = "Spaces region"
  value       = var.spaces_region
}

# ── DNS ──────────────────────────────────────────────────────────────────────

output "api_url" {
  description = "API endpoint URL"
  value       = "https://api.${var.domain}"
}

output "app_url" {
  description = "Frontend application URL"
  value       = "https://app.${var.domain}"
}

output "media_url" {
  description = "Media CDN URL"
  value       = "https://media.${var.domain}"
}

output "alert_email" {
  description = "Alert/contact email (pass-through from variable)"
  value       = var.alert_email
}

# ── Summary ──────────────────────────────────────────────────────────────────

output "summary" {
  description = "Infrastructure summary"
  value = <<-EOT

    ===== ListingAI DigitalOcean Infrastructure =====

    Droplet:    ${digitalocean_droplet.app.ipv4_address} (${var.droplet_size})
    SSH:        ssh deploy@${digitalocean_droplet.app.ipv4_address}

    Postgres:   ${digitalocean_database_cluster.postgres.private_host}:${digitalocean_database_cluster.postgres.port}
    Redis:      ${digitalocean_database_cluster.redis.private_host}:${digitalocean_database_cluster.redis.port}
    Spaces:     https://${var.spaces_region}.digitaloceanspaces.com/${digitalocean_spaces_bucket.media.name}
    CDN:        ${digitalocean_cdn.media.endpoint}

    API:        https://api.${var.domain}
    App:        https://app.${var.domain}
    Media:      https://media.${var.domain}

    Next step:  ./deploy.sh

  EOT
}
