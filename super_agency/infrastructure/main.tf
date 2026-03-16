# Digital Labour AWS Infrastructure
# Terraform configuration for distributed command center

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "digital-labour-terraform-state"
    key            = "distributed-command-center/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "digital-labour-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Digital Labour"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# VPC Configuration
module "vpc" {
  source = "./modules/vpc"

  name = "digital-labour-${var.environment}"
  cidr = var.vpc_cidr

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment == "dev"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "digital-labour-vpc"
  }
}

# Security Groups
resource "aws_security_group" "command_center" {
  name_prefix = "digital-labour-command-center-"
  description = "Security group for Digital Labour Command Center"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr_blocks
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Operations API"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = var.allowed_api_cidr_blocks
  }

  ingress {
    description = "Matrix Monitor"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = var.allowed_monitor_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "digital-labour-command-center-sg"
  }
}

# EC2 Instances for Compute
module "compute_instances" {
  source = "./modules/ec2"

  for_each = var.compute_instances

  name = "digital-labour-compute-${each.key}"

  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = each.value.instance_type
  key_name                    = aws_key_pair.digital_labour.key_name
  vpc_security_group_ids      = [aws_security_group.command_center.id]
  subnet_id                   = module.vpc.private_subnets[0]
  associate_public_ip_address = false

  user_data = templatefile("${path.module}/templates/user_data.sh.tpl", {
    environment = var.environment
    region      = var.aws_region
  })

  root_block_device = [
    {
      volume_type = "gp3"
      volume_size = each.value.volume_size
      encrypted   = true
    }
  ]

  tags = {
    Name        = "digital-labour-compute-${each.key}"
    Role        = "compute"
    InstanceType = each.value.instance_type
  }
}

# Auto Scaling Group for Dynamic Compute
resource "aws_launch_template" "compute" {
  name_prefix   = "digital-labour-compute-"
  image_id      = data.aws_ami.amazon_linux_2.id
  instance_type = "t3.medium"
  key_name      = aws_key_pair.digital_labour.key_name

  vpc_security_group_ids = [aws_security_group.command_center.id]

  user_data = base64encode(templatefile("${path.module}/templates/user_data.sh.tpl", {
    environment = var.environment
    region      = var.aws_region
  }))

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 20
      volume_type = "gp3"
      encrypted   = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "digital-labour-compute-asg"
      Role        = "compute"
      Environment = var.environment
    }
  }
}

resource "aws_autoscaling_group" "compute" {
  name_prefix         = "digital-labour-compute-"
  desired_capacity    = var.asg_desired_capacity
  max_size           = var.asg_max_size
  min_size           = var.asg_min_size
  vpc_zone_identifier = module.vpc.private_subnets

  launch_template {
    id      = aws_launch_template.compute.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "digital-labour-compute-asg"
    propagate_at_launch = true
  }

  tag {
    key                 = "Role"
    value               = "compute"
    propagate_at_launch = true
  }
}

# S3 Storage
resource "aws_s3_bucket" "storage" {
  bucket = "digital-labour-${var.environment}-storage"

  tags = {
    Name = "digital-labour-storage"
  }
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "storage" {
  bucket = aws_s3_bucket.storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Distribution for Global Access
resource "aws_cloudfront_distribution" "command_center" {
  count = var.enable_cloudfront ? 1 : 0

  origin {
    domain_name = aws_s3_bucket.storage.bucket_regional_domain_name
    origin_id   = "digital-labour-storage"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.command_center[0].cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "digital-labour-storage"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "digital-labour-command-center"
  }
}

resource "aws_cloudfront_origin_access_identity" "command_center" {
  count = var.enable_cloudfront ? 1 : 0

  comment = "Digital Labour Command Center OAI"
}

# RDS Database (optional)
resource "aws_db_instance" "command_center" {
  count = var.enable_database ? 1 : 0

  identifier           = "digital-labour-${var.environment}"
  engine              = "postgres"
  engine_version      = "15.3"
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  storage_type        = "gp3"
  storage_encrypted   = true

  db_name  = "digitallabour"
  username = var.db_username
  password = var.db_password
  port     = 5432

  vpc_security_group_ids = [aws_security_group.database[0].id]
  db_subnet_group_name   = aws_db_subnet_group.command_center[0].name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  multi_az               = var.environment == "prod"
  skip_final_snapshot    = var.environment != "prod"

  tags = {
    Name = "digital-labour-database"
  }
}

# ElastiCache Redis (optional)
resource "aws_elasticache_cluster" "command_center" {
  count = var.enable_redis ? 1 : 0

  cluster_id           = "digital-labour-${var.environment}"
  engine              = "redis"
  node_type           = var.redis_node_type
  num_cache_nodes     = 1
  parameter_group_name = "default.redis7"
  port                = 6379

  subnet_group_name = aws_elasticache_subnet_group.command_center[0].name
  security_group_ids = [aws_security_group.cache[0].id]

  tags = {
    Name = "digital-labour-redis"
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "command_center" {
  name        = "digital-labour-command-center"
  description = "Digital Labour Command Center API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "operations" {
  rest_api_id = aws_api_gateway_rest_api.command_center.id
  parent_id   = aws_api_gateway_rest_api.command_center.root_resource_id
  path_part   = "operations"
}

resource "aws_api_gateway_method" "operations_get" {
  rest_api_id   = aws_api_gateway_rest_api.command_center.id
  resource_id   = aws_api_gateway_resource.operations.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.command_center.id
}

# Lambda Functions
resource "aws_lambda_function" "operations_api" {
  filename         = "lambda_functions.zip"
  function_name    = "digital-labour-operations-api"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "operations_api.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
      REGION      = var.aws_region
    }
  }

  tags = {
    Name = "digital-labour-operations-api"
  }
}

# CloudWatch Monitoring
resource "aws_cloudwatch_dashboard" "command_center" {
  dashboard_name = "digital-labour-command-center"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", "${module.compute_instances["primary"].id}"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Compute Instance CPU Utilization"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "BucketSizeBytes", "BucketName", aws_s3_bucket.storage.bucket]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "S3 Storage Usage"
          period  = 300
        }
      }
    ]
  })
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "compute_instance_ids" {
  description = "Compute instance IDs"
  value       = [for instance in module.compute_instances : instance.id]
}

output "s3_bucket_name" {
  description = "S3 storage bucket name"
  value       = aws_s3_bucket.storage.bucket
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = aws_api_gateway_deployment.command_center.invoke_url
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.command_center[0].domain_name : null
}