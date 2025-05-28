# Security Configuration Guide

## 🔐 Credentials Setup Instructions

### 1. Reddit API Credentials

**Where to get them:**
- Go to: https://www.reddit.com/prefs/apps
- Click "Create App" or "Create Another App"
- Choose "script" type
- Note down:
  - Client ID (under the app name)
  - Client Secret

**Where to put them:**
- Copy `.env.example` to `.env`
- Replace `your_reddit_client_id_here` with your actual Client ID
- Replace `your_reddit_client_secret_here` with your actual Client Secret
- Replace `your_app_name/1.0` with a descriptive user agent

### 2. GitHub Personal Access Token

**Where to get it:**
- Go to: https://github.com/settings/tokens
- Click "Generate new token (classic)"
- Select scopes: `repo`, `workflow`, `write:packages`
- Copy the generated token

**Where to put it:**
- In `.env` file: Replace `your_github_personal_access_token_here`
- In GitHub repository secrets (for CI/CD):
  - Go to your repo → Settings → Secrets and variables → Actions
  - Add secrets:
    - `REDDIT_CLIENT_ID`
    - `REDDIT_CLIENT_SECRET` 
    - `GITHUB_TOKEN_PAT`

### 3. Server Deployment Credentials (for Step 10+)

**SSH Access:**
- Generate SSH key: `ssh-keygen -t ed25519 -C "ci-cd-key"`
- Add public key to server: `~/.ssh/authorized_keys`
- Add private key to GitHub secrets as `SSH_PRIVATE_KEY`

**GitHub Secrets for Deployment:**
```
SSH_HOST=your_server_ip_or_domain
SSH_USER=cayir
SSH_PRIVATE_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
SSH_PORT=22
```

### 4. Security Best Practices

✅ **DO:**
- Use the `.env.example` as template
- Keep actual credentials in `.env` (gitignored)
- Use GitHub Secrets for CI/CD
- Rotate credentials regularly
- Use least-privilege access

❌ **DON'T:**
- Commit actual credentials to Git
- Share credentials in chat/email
- Use production credentials for development
- Hard-code secrets in source code

### 5. Current Status

Your credentials have been secured:
- ✅ `.gitignore` created to protect sensitive files
- ✅ Actual credentials removed from tracked `.env`
- ✅ Template `.env.example` ready for configuration
- ✅ Backup saved to `.env.backup` (gitignored)

**Next steps:**
1. Fill in your actual credentials in `.env`
2. Add GitHub repository secrets
3. Test the application locally
4. Continue with Step 10 (Server Deployment)
