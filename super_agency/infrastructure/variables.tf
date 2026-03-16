# Digital Labour AWS Infrastructure Variables

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "allowed_ssh_cidr_blocks" {
  description = "CIDR blocks allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict in production
}

variable "allowed_api_cidr_blocks" {
  description = "CIDR blocks allowed to access API"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict in production
}

variable "allowed_monitor_cidr_blocks" {
  description = "CIDR blocks allowed to access Matrix Monitor"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict in production
}

variable "compute_instances" {
  description = "Compute instance configurations"
  type = map(object({
    instance_type = string
    volume_size   = number
  }))
  default = {
    primary = {
      instance_type = "t3.medium"
      volume_size   = 20
    }
    secondary = {
      instance_type = "t3.small"
      volume_size   = 20
    }
  }
}

variable "asg_desired_capacity" {
  description = "Auto Scaling Group desired capacity"
  type        = number
  default     = 2
}

variable "asg_max_size" {
  description = "Auto Scaling Group maximum size"
  type        = number
  default     = 10
}

variable "asg_min_size" {
  description = "Auto Scaling Group minimum size"
  type        = number
  default     = 1
}

variable "enable_cloudfront" {
  description = "Enable CloudFront distribution"
  type        = bool
  default     = true
}

variable "enable_database" {
  description = "Enable RDS database"
  type        = bool
  default     = false
}

variable "enable_redis" {
  description = "Enable ElastiCache Redis"
  type        = bool
  default     = false
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_username" {
  description = "RDS database username"
  type        = string
  default     = "digitallabour"
  sensitive   = true
}

variable "db_password" {
  description = "RDS database password"
  type        = string
  sensitive   = true
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# SSH Key Pair
variable "ssh_public_key" {
  description = "SSH public key for EC2 instances"
  type        = string
  default     = "" # Set via environment or tfvars
}

# Domain and SSL (for production)
variable "domain_name" {
  description = "Domain name for the command center"
  type        = string
  default     = ""
}

variable "ssl_certificate_arn" {
  description = "ARN of SSL certificate for CloudFront"
  type        = string
  default     = ""
}

# Monitoring and Alerting
variable "enable_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""
}

# Cost Optimization
variable "enable_cost_allocation_tags" {
  description = "Enable cost allocation tags"
  type        = bool
  default     = true
}

variable "budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 100
}

# Backup Configuration
variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

# Scaling Configuration
variable "cpu_utilization_high_threshold" {
  description = "CPU utilization threshold for scaling up"
  type        = number
  default     = 70
}

variable "cpu_utilization_low_threshold" {
  description = "CPU utilization threshold for scaling down"
  type        = number
  default     = 30
}

# Security
variable "enable_waf" {
  description = "Enable AWS WAF for API protection"
  type        = bool
  default     = false
}

variable "enable_guardduty" {
  description = "Enable Amazon GuardDuty"
  type        = bool
  default     = true
}

variable "enable_config" {
  description = "Enable AWS Config"
  type        = bool
  default     = true
}

# Tagging
variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}