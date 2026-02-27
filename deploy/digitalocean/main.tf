# ──────────────────────────────────────────────────────────────────────────────
# ListingAI — DigitalOcean Infrastructure
# Estimated cost: ~$59/mo (Droplet $24 + Postgres $15 + Redis $15 + Spaces $5)
# ──────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.36"
    }
  }
}

provider "digitalocean" {
  token             = var.do_token
  spaces_access_id  = var.spaces_access_key
  spaces_secret_key = var.spaces_secret_key
}

# ──────────────────────────────────────────────────────────────────────────────
# Project — groups all resources in the DO console
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_project" "listingai" {
  name        = "ListingAI"
  description = "Multi-tenant AI-powered real estate marketing SaaS"
  purpose     = "Web Application"
  environment = "Production"

  resources = [
    digitalocean_droplet.app.urn,
    digitalocean_database_cluster.postgres.urn,
    digitalocean_database_cluster.redis.urn,
    digitalocean_spaces_bucket.media.urn,
    digitalocean_domain.main.urn,
  ]
}

# ──────────────────────────────────────────────────────────────────────────────
# VPC — private network for inter-service communication
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_vpc" "listingai" {
  name     = "listingai-vpc"
  region   = var.region
  ip_range = "10.10.10.0/24"
}

# ──────────────────────────────────────────────────────────────────────────────
# Droplet — application server (Docker host)
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_droplet" "app" {
  name     = "listingai-app"
  image    = "docker-24-04"
  size     = var.droplet_size
  region   = var.region
  vpc_uuid = digitalocean_vpc.listingai.id

  ssh_keys = [var.ssh_key_fingerprint]

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    github_repo   = var.github_repo
    github_branch = var.github_branch
  })

  tags = ["listingai", "production"]

  # Graceful replacement on user_data change
  lifecycle {
    create_before_destroy = true
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Managed PostgreSQL (db-s-1vcpu-1gb, $15/mo)
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_database_cluster" "postgres" {
  name                 = "listingai-pg"
  engine               = "pg"
  version              = var.postgres_version
  size                 = var.db_size
  region               = var.region
  node_count           = 1
  private_network_uuid = digitalocean_vpc.listingai.id

  tags = ["listingai", "production"]
}

resource "digitalocean_database_db" "listingai" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "listingai"
}

resource "digitalocean_database_user" "listingai" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "listingai"
}

# Connection pool for better connection management
resource "digitalocean_database_connection_pool" "listingai" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "listingai-pool"
  mode       = "transaction"
  size       = 15
  db_name    = digitalocean_database_db.listingai.name
  user       = digitalocean_database_user.listingai.name
}

# Restrict database access to VPC only
resource "digitalocean_database_firewall" "postgres" {
  cluster_id = digitalocean_database_cluster.postgres.id

  rule {
    type  = "droplet"
    value = digitalocean_droplet.app.id
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Managed Redis (db-s-1vcpu-1gb, $15/mo)
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_database_cluster" "redis" {
  name                 = "listingai-redis"
  engine               = "redis"
  version              = var.redis_version
  size                 = var.db_size
  region               = var.region
  node_count           = 1
  private_network_uuid = digitalocean_vpc.listingai.id

  tags = ["listingai", "production"]
}

# Restrict Redis access to VPC only
resource "digitalocean_database_firewall" "redis" {
  cluster_id = digitalocean_database_cluster.redis.id

  rule {
    type  = "droplet"
    value = digitalocean_droplet.app.id
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Spaces — S3-compatible object storage ($5/mo for 250GB)
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_spaces_bucket" "media" {
  name   = "listingai-media"
  region = var.spaces_region
  acl    = "private"

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = [
      "https://app.${var.domain}",
      "https://api.${var.domain}",
    ]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    enabled = true

    # Clean up incomplete multipart uploads after 7 days
    abort_incomplete_multipart_upload_days = 7
  }
}

# CDN for serving media assets
resource "digitalocean_cdn" "media" {
  origin         = digitalocean_spaces_bucket.media.bucket_domain_name
  custom_domain  = "media.${var.domain}"
  ttl            = 3600

  depends_on = [digitalocean_spaces_bucket.media]
}

# ──────────────────────────────────────────────────────────────────────────────
# Firewall — restrict inbound traffic
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_firewall" "app" {
  name        = "listingai-firewall"
  droplet_ids = [digitalocean_droplet.app.id]

  # SSH
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # HTTP (redirects to HTTPS via nginx)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # HTTPS
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Allow all outbound TCP
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Allow all outbound UDP (DNS, NTP, etc.)
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # ICMP outbound (ping, traceroute)
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  tags = ["listingai"]
}

# ──────────────────────────────────────────────────────────────────────────────
# DNS — A records for the domain
# ──────────────────────────────────────────────────────────────────────────────

resource "digitalocean_domain" "main" {
  name = var.domain
}

# api.listingai.com -> Droplet
resource "digitalocean_record" "api" {
  domain = digitalocean_domain.main.id
  type   = "A"
  name   = "api"
  value  = digitalocean_droplet.app.ipv4_address
  ttl    = 300
}

# app.listingai.com -> Droplet
resource "digitalocean_record" "app" {
  domain = digitalocean_domain.main.id
  type   = "A"
  name   = "app"
  value  = digitalocean_droplet.app.ipv4_address
  ttl    = 300
}

# Root domain -> Droplet
resource "digitalocean_record" "root" {
  domain = digitalocean_domain.main.id
  type   = "A"
  name   = "@"
  value  = digitalocean_droplet.app.ipv4_address
  ttl    = 300
}

# media.listingai.com -> CDN (CNAME for Spaces CDN)
resource "digitalocean_record" "media" {
  domain = digitalocean_domain.main.id
  type   = "CNAME"
  name   = "media"
  value  = "${digitalocean_cdn.media.endpoint}."
  ttl    = 3600
}
