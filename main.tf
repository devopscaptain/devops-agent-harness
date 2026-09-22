terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Staging bucket for AWS MGN/DMS migration artifacts.
# NOTE: this is currently failing the org compliance guardrail scan.
resource "aws_s3_bucket" "migration_artifacts" {
  bucket = "acme-migration-artifacts-stage"
}
