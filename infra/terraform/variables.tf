variable "aws_region" {
  description = "AWS region for the site origin and Terraform resources."
  type        = string
  default     = "us-east-1"
}

variable "domain_name" {
  description = "Primary Loki Agent hostname."
  type        = string
  default     = "loki.computer"
}

variable "hosted_zone_id" {
  description = "Existing public Route53 hosted zone ID for loki.computer. Override only when deploying a different zone."
  type        = string
  default     = "Z09046593O6AIZUOSG6X8"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}

variable "doku_origin_domain" {
  description = "Doku portal renderer origin proxied by CloudFront."
  type        = string
  default     = "doku.sh"
}
