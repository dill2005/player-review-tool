# U12 Player Review Tool

A web app for football coaches to generate FA Four Corner Model player reviews as PDFs.

## Deployment on Render (free)

### Step 1 — Get your Anthropic API Key
1. Go to https://console.anthropic.com
2. Sign up for a free account
3. Click "API Keys" in the left menu
4. Click "Create Key" and copy the key (starts with sk-ant-...)
5. Add a small amount of credit (£5 will do hundreds of reports)

### Step 2 — Put the code on GitHub
1. Go to https://github.com and create a free account
2. Click the "+" button → "New repository"
3. Name it "player-review-tool", keep it Public, click "Create repository"
4. Upload all files from this folder (app.py, requirements.txt, Procfile)

### Step 3 — Deploy on Render
1. Go to https://render.com and sign up with your GitHub account
2. Click "New +" → "Web Service"
3. Connect your GitHub repo "player-review-tool"
4. Settings:
   - Name: player-review-tool
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn app:app
5. Click "Advanced" → "Add Environment Variable"
   - Key: ANTHROPIC_API_KEY
   - Value: (paste your key from Step 1)
6. Click "Create Web Service"
7. Wait 2-3 minutes for it to deploy
8. Your URL will be: https://player-review-tool.onrender.com

Share that URL with all your coaches!
