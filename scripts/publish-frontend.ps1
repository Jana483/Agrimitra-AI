$stack = "agrimitra-ai"
$region = "ap-southeast-2"
$bucket = aws cloudformation describe-stacks --stack-name $stack --region $region --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" --output text
if (-not $bucket) { throw "Website bucket output was not found. Deploy the stack first." }
aws s3 cp templates/index.html "s3://$bucket/index.html" --region $region --content-type "text/html; charset=utf-8"
Write-Host "Published dashboard to s3://$bucket/index.html"
