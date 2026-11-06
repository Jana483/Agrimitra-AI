# AgriMitra AI live demo

Use this order when you show the project. The notebook proves the decision API. The browser shows the farmer dashboard.

## 1. Open the project

```powershell
cd C:\Users\DELL\Projects\Agrimitra-AI
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt notebook
```

## 2. Run the Jupyter notebook

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m notebook notebooks\Agrimitra_AI_Demo.ipynb
```

In Jupyter, use **Cell → Run All**.

The notebook calls the same API as the website. It does not need AWS credentials. It prints:

1. Weather and spray advice for Nashik
2. Crops to grow on black soil in Kharif
3. Climate risk for wheat at grain filling
4. Mandi prices and where to sell onion
5. A short farmer question in English
6. The AWS services used in `ap-southeast-2`

## 3. Show the dashboard

In a second terminal:

```powershell
cd C:\Users\DELL\Projects\Agrimitra-AI
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" app.py
```

Open http://127.0.0.1:5000 and walk through these clicks:

1. Leave the location on Maharashtra. Show the 7-day weather card and the spray or harvest advice.
2. Open **Climate Risk Advisor**. Choose Wheat, grain filling, Punjab. Show the risk score and the PMFBY 72-hour claim note.
3. Open crop advice. Season Kharif, black soil, medium water. Show the top crop and the fertilizer stages.
4. Open mandi prices for Onion. Show modal price against MSP.
5. Ask the chat, in English: `How do I protect crops from unseasonal rainfall?`

This address works only on this computer. It is not the public demo link.

## 4. Publish the public AWS demo

The account is `313313524206`, region `ap-southeast-2`, profile `myproject`. Run this in the same CloudShell where `aws sts get-caller-identity --profile myproject` succeeded.

```bash
cd ~/agrimitra-deploy
aws cloudformation describe-stacks \
  --stack-name agrimitra-ai \
  --region ap-southeast-2 \
  --profile myproject \
  --query "Stacks[0].StackStatus" \
  --output text
```

Wait until the status is `CREATE_COMPLETE`. Then upload the dashboard and print the public URL:

```bash
cd ~/agrimitra-deploy
WEB=$(aws cloudformation describe-stacks \
  --stack-name agrimitra-ai \
  --region ap-southeast-2 \
  --profile myproject \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucket'].OutputValue" \
  --output text)
aws s3 cp templates/index.html "s3://${WEB}/index.html" \
  --region ap-southeast-2 \
  --profile myproject \
  --content-type "text/html; charset=utf-8"
aws cloudformation describe-stacks \
  --stack-name agrimitra-ai \
  --region ap-southeast-2 \
  --profile myproject \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" \
  --output text
```

Paste that `https://....cloudfront.net` address into **Endpoint or live demo**.

If the stack command says the stack does not exist, create it once:

```bash
cd ~/agrimitra-deploy
aws s3 mb s3://agrimitra-cfn-313313524206-apse2 --region ap-southeast-2 --profile myproject
aws cloudformation package \
  --template-file infrastructure/template.yaml \
  --s3-bucket agrimitra-cfn-313313524206-apse2 \
  --output-template-file packaged.yaml \
  --region ap-southeast-2 \
  --profile myproject
aws cloudformation deploy \
  --template-file packaged.yaml \
  --stack-name agrimitra-ai \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --region ap-southeast-2 \
  --profile myproject \
  --parameter-overrides BedrockModelId=amazon.nova-lite-v1:0
```

CloudFront often takes 10 to 20 minutes. Leave CloudShell open until the deploy command returns.
