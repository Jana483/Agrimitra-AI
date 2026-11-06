#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v sam >/dev/null 2>&1; then
  echo "Install the AWS SAM CLI, then run this script again."
  exit 1
fi

sam build --template-file infrastructure/template.yaml
sam deploy --template-file .aws-sam/build/template.yaml --config-file samconfig.toml

bucket="$(aws cloudformation describe-stacks --stack-name agrimitra-ai --region ap-southeast-2 --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucket'].OutputValue" --output text)"
aws s3 cp templates/index.html "s3://${bucket}/index.html" --region ap-southeast-2 --content-type "text/html; charset=utf-8"
echo "Dashboard uploaded. Open the CloudFrontUrl output."
