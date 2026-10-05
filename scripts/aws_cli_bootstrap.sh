#!/usr/bin/env bash
# One-time AWS CLI helper: verify credentials and create the artifact bucket.
set -euo pipefail
: "${BUCKET_NAME:?set BUCKET_NAME}"
REGION="${AWS_REGION:-ap-south-1}"
aws sts get-caller-identity >/dev/null && echo "credentials OK"
aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null || \
  aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
echo "bucket ready: $BUCKET_NAME"
