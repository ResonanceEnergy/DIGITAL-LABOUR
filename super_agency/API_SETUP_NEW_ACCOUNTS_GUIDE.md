# 🔍 API Examination & New Account Creation Guide
## BIT RAGE LABOUR API Setup & Email Accounts

## 🎯 **PHASE 1: YouTube Data API v3 Setup**

### **Current Status Check:**
```bash
# Test current API status
python youtube_intelligence_monitor.py
# Look for: "No YouTube API key found" message
```

### **Google Cloud Console Setup:**

1. **Access Google Cloud:**
   - Go to: https://console.cloud.google.com/
   - Sign in with your Google account
   - Select/Create project: `agent-bravo-487119`

2. **Enable YouTube Data API v3:**
   - Go to: "APIs & Services" → "Library"
   - Search for: "YouTube Data API v3"
   - Click: "Enable"

3. **Create API Credentials:**
   - Go to: "APIs & Services" → "Credentials"
   - Click: "Create Credentials" → "API Key"
   - Copy the generated API key

4. **Restrict API Key (Security):**
   - Click on the API key
   - Add restrictions:
     - **Application restrictions:** "IP addresses"
     - **API restrictions:** "Restrict key" → Select "YouTube Data API v3"
   - Save restrictions

### **API Key Configuration:**
```bash
# Option 1: Environment Variable (Recommended)
$env:YOUTUBE_API_KEY = "your_api_key_here"

# Option 2: Add to config file
# Edit inner_council_config.json
{
  "youtube_api_key": "your_api_key_here"
}
```

## 📧 **PHASE 2: New Microsoft Account Creation**

### **Recommended New Accounts:**

1. **council52@yourdomain.onmicrosoft.com**
   - Purpose: Council 52 intelligence operations
   - Permissions: Full access to intelligence systems

2. **operations@yourdomain.onmicrosoft.com**
   - Purpose: BIT RAGE LABOUR operations
   - Permissions: SendAs, FullAccess across tenant

3. **intelligence@yourdomain.onmicrosoft.com**
   - Purpose: AI agent communications
   - Permissions: Automated intelligence distribution

4. **admin@yourdomain.onmicrosoft.com**
   - Purpose: Administrative operations
   - Permissions: Global admin access

### **Account Creation Steps:**

1. **Microsoft 365 Admin Center:**
   - Go to: https://admin.microsoft.com/
   - Sign in with admin account
   - Go to: "Users" → "Active users" → "Add a user"

2. **For Each New Account:**
   - **Display name:** Council 52 Intelligence, etc.
   - **Username:** council52@yourdomain.onmicrosoft.com
   - **Domain:** Select your custom domain
   - **Location:** Your region
   - **Roles:** Assign appropriate admin roles

3. **License Assignment:**
   - Assign: Microsoft 365 Business Premium or higher
   - This includes Exchange Online, Teams, etc.

4. **Security Setup:**
   - Set strong passwords
   - Enable MFA (Multi-Factor Authentication)
   - Configure security defaults

## 🔑 **PHASE 3: API Integration Setup**

### **YouTube API Integration:**
```json
// Add to inner_council_config.json
{
  "api_config": {
    "youtube": {
      "api_key": "your_api_key_here",
      "quota_limit": 10000,
      "rate_limit": "per day",
      "channels_per_request": 50
    }
  }
}
```

### **Microsoft Graph API Setup:**
1. **Azure Portal:**
   - Go to: https://portal.azure.com/
   - Navigate to: "Azure Active Directory" → "App registrations"

2. **Register Application:**
   - Name: "BIT RAGE LABOUR Council 52"
   - Supported account types: "Accounts in this organizational directory"
   - Redirect URI: Leave blank for now

3. **API Permissions:**
   - Add: "Microsoft Graph"
   - Permissions:
     - Mail.ReadWrite
     - Mail.Send
     - User.Read.All
     - Group.ReadWrite.All

4. **Client Secret:**
   - Go to: "Certificates & secrets"
   - Create new client secret
   - Copy the secret value (save securely!)

### **Environment Configuration:**
```bash
# Set environment variables
$env:YOUTUBE_API_KEY = "your_youtube_api_key"
$env:AZURE_CLIENT_ID = "your_app_id"
$env:AZURE_CLIENT_SECRET = "your_client_secret"
$env:AZURE_TENANT_ID = "your_tenant_id"
```

## 📊 **PHASE 4: Testing & Verification**

### **YouTube API Test:**
```bash
python youtube_intelligence_monitor.py
# Should show: "YouTube API key found"
# Should process real channel data
```

### **Microsoft Account Test:**
```bash
# Test mailbox access
Get-Mailbox -Identity "council52@yourdomain.onmicrosoft.com"

# Test permissions
Get-MailboxPermission -Identity "council52@yourdomain.onmicrosoft.com"
```

### **Full System Test:**
```bash
# Run complete Council 52 intelligence gathering
python youtube_intelligence_monitor.py

# Check reports directory
ls inner_council_intelligence/
ls daily_policy_directives/
```

## 🎯 **PHASE 5: Council 52 Activation**

### **With Live APIs:**
- **Real-time intelligence** from 47 human sources
- **Automated email distribution** via new accounts
- **Cross-platform integration** (YouTube + Microsoft)
- **Supreme coordination** via Agent AZ

### **Expected Outcomes:**
- ✅ Live YouTube data processing
- ✅ Automated intelligence reports
- ✅ Email notifications from new accounts
- ✅ Full Council 52 operational capability

---

## 🚀 **Ready to Begin?**

**Start with YouTube API setup:**
1. Go to: https://console.cloud.google.com/
2. Enable YouTube Data API v3
3. Create and restrict API key
4. Test with: `python youtube_intelligence_monitor.py`

**Then create Microsoft accounts:**
1. Go to: https://admin.microsoft.com/
2. Add new users with custom domain
3. Assign licenses and permissions
4. Configure API access

**Let's activate the full Council 52 intelligence system!** 🏛️⚡🧠</content>
<parameter name="filePath">C:\Dev\DIGITAL-LABOUR\API_SETUP_NEW_ACCOUNTS_GUIDE.md