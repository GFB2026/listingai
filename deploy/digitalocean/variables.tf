# ──────────────────────────────────────────────────────────────────────────────
# ListingAI — DigitalOcean Infrastructure Variables
# ──────────────────────────────────────────────────────────────────────────────

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "ssh_key_fingerprint" {
  description = "SSH key fingerprint already registered in DigitalOcean"
  type        = string
}

variable "domain" {
  description = "Root domain name for the application"
  type        = string
  default     = "listingai.com"
}

variable "region" {
  description = "DigitalOcean region for compute and database resources"
  type        = string
  default     = "nyc1"
}

variable "spaces_region" {
  description = "DigitalOcean region for Spaces object storage (limited availability)"
  type        = string
  default     = "nyc3"
}

variable "droplet_size" {
  description = "Droplet size slug (s-2vcpu-4gb = $24/mo)"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "db_size" {
  description = "Managed database size slug (db-s-1vcpu-1gb = $15/mo)"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

variable "postgres_version" {
  description = "PostgreSQL major version for managed database"
  type        = string
  default     = "16"
}

variable "redis_version" {
  description = "Redis major version for managed database"
  type        = string
  default     = "7"
}

variable "github_repo" {
  description = "GitHub repository URL for the listingai project"
  type        = string
  default     = "https://github.com/your-org/listingai.git"
}

variable "github_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "main"
}

variable "alert_email" {
  description = "Email address for Let's Encrypt and infrastructure alerts"
  type        = string
  default     = "greg@gregfredabytes.com"
}

# ──────────────────────────────────────────────────────────────────────────────
# Spaces access keys (generated in DO console under API > Spaces Keys)
# ──────────────────────────────────────────────────────────────────────────────

variable "spaces_access_key" {
  description = "DigitalOcean Spaces access key ID"
  type        = string
  sensitive   = true
}

variable "spaces_secret_key" {
  description = "DigitalOcean Spaces secret access key"
  type        = string
  sensitive   = true
}
