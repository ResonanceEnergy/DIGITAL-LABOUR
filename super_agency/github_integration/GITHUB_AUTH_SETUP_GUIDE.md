# GitHub Authentication Setup Guide
## DIGITAL LABOUR ResonanceEnergy Organization Access

**Date:** February 20, 2026
**Status:** Ready for Token Configuration

---

## 🎯 Authentication Setup Complete

The GitHub integration system is configured and ready. You just need to add your GitHub Personal Access Token.

### 📋 What Was Set Up

#### **Files Created:**
- ✅ `.env` - Environment variables template
- ✅ `.gitignore` - Security exclusions
- ✅ `setup_auth.py` - Authentication testing script
- ✅ Configuration files ready

#### **System Configuration:**
- ✅ Organization: `ResonanceEnergy`
- ✅ API endpoints configured
- ✅ Authentication framework ready
- ✅ Security settings prepared

---

## 🔑 Token Setup Instructions

### Step 1: Generate GitHub Personal Access Token

1. **Go to:** https://github.com/settings/tokens
2. **Click:** "Generate new token (classic)"
3. **Name:** "DIGITAL LABOUR Integration"
4. **Expiration:** Select appropriate timeframe (recommend 90 days)
5. **Select scopes:**
   - ✅ `repo` - Full control of private repositories
   - ✅ `workflow` - Update GitHub Action workflows
   - ✅ `read:org` - Read org and team membership
   - ✅ `write:org` - Read and write org and team membership
   - ✅ `admin:org` - Fully manage org and teams
   - ✅ `admin:repo_hook` - Full control of repository hooks
   - ✅ `admin:public_key` - Full control of public keys
   - ✅ `admin:repo` - Full control of repositories

6. **Generate token** and **copy it immediately** (you won't see it again!)

### Step 2: Configure Token in DIGITAL LABOUR

**Option A: Update .env file (Recommended)**
```bash
# Edit the .env file in github_integration directory
# Replace 'your_personal_access_token_here' with your actual token
```

**Option B: Set Environment Variable**
```bash
# Linux/Mac
export GITHUB_TOKEN=your_actual_token_here

# Windows PowerShell
$env:GITHUB_TOKEN = "your_actual_token_here"
```

### Step 3: Test Authentication

```bash
# Navigate to github_integration directory
cd github_integration

# Test authentication setup
python3 setup_auth.py
```

**Expected Output:**
```
🔐 DIGITAL LABOUR GitHub Authentication Setup
==================================================
✅ Loaded environment from .env file
✅ GITHUB_TOKEN found: ghp_1234****************************abcd
✅ GitHub API connection successful
   Authenticated as: your-username
✅ Organization access confirmed: Resonance Energy
✅ Token has required scopes
==================================================
🎉 GitHub Authentication Setup Complete!
```

### Step 4: Run GitHub Integration

Once authentication is confirmed:

```bash
# Sync all portfolio repositories
./run_github_integration.sh sync

# Create a test repository
./run_github_integration.sh create test-repo

# Setup security for existing repository
./run_github_integration.sh setup my-project
```

---

## 🔒 Security Best Practices

### Token Management
- **Never commit** `.env` file to version control
- **Rotate tokens** regularly (every 30-90 days)
- **Monitor usage** in GitHub security settings
- **Use minimal scopes** required for operations

### Access Control
- **Limit organization access** to necessary team members
- **Use branch protection** rules for all repositories
- **Enable 2FA** on all GitHub accounts
- **Regular security audits** of repository access

### Operational Security
- **Log all operations** for audit trails
- **Monitor API usage** and rate limits
- **Backup configurations** securely
- **Test integrations** in development first

---

## 🚨 Troubleshooting

### Common Issues

#### **"GITHUB_TOKEN not found"**
- Check that `.env` file exists and contains the token
- Ensure token is not the placeholder value
- Try setting environment variable directly

#### **"Authentication failed - invalid token"**
- Verify token was copied correctly
- Check token hasn't expired
- Regenerate token if necessary

#### **"Organization access denied"**
- Confirm you're a member of ResonanceEnergy org
- Check organization permissions
- Verify token has `read:org` and `write:org` scopes

#### **"Missing required scopes"**
- Regenerate token with all required scopes
- Check GitHub token settings page

### Getting Help

If issues persist:
1. Run `python3 setup_auth.py` for detailed diagnostics
2. Check `AUTH_SETUP_SUMMARY.md` for status
3. Review GitHub token settings and scopes
4. Contact DIGITAL LABOUR Council for access issues

---

## 🎯 What Happens Next

Once authentication is working, the system will:

1. **Sync Portfolio** - Create/update all repositories from portfolio.json
2. **Apply Security** - Set up CodeQL, Dependabot, branch protection
3. **Deploy CI/CD** - Install workflow templates and automation
4. **Monitor Health** - Track repository status and compliance
5. **Enable Governance** - Automate DIGITAL LABOUR operational standards

---

## 📞 Support

**Setup Issues:** Run `python3 setup_auth.py` for diagnostics
**Integration Help:** Check `GITHUB_INTEGRATION_GUIDE.md`
**Security Concerns:** Contact DIGITAL LABOUR Council immediately

---

*DIGITAL LABOUR GitHub Authentication Setup Guide v1.0*