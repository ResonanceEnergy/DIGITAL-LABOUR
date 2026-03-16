# Microsoft Account Creation Script - Digital Labour
# Creates new accounts for Council 52 operations

param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,

    [Parameter(Mandatory=$true)]
    [string]$AdminUsername,

    [Parameter(Mandatory=$false)]
    [string]$Location = "US"
)

# Connect to Microsoft 365
Write-Host "🔗 Connecting to Microsoft 365..." -ForegroundColor Cyan
try {
    Connect-MsolService
    Write-Host "✅ Connected successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to connect. Please run: Connect-MsolService" -ForegroundColor Red
    exit 1
}

# New account configurations
$accounts = @(
    @{
        Name = "Council 52 Intelligence"
        Username = "council52@$Domain"
        Role = "Intelligence Operations"
    },
    @{
        Name = "Digital Labour Operations"
        Username = "operations@$Domain"
        Role = "Operations Management"
    },
    @{
        Name = "AI Intelligence Agent"
        Username = "intelligence@$Domain"
        Role = "AI Communications"
    },
    @{
        Name = "Digital Labour Admin"
        Username = "admin@$Domain"
        Role = "Administrative Operations"
    }
)

# Create accounts
foreach ($account in $accounts) {
    Write-Host "`n📧 Creating account: $($account.Username)" -ForegroundColor Yellow

    try {
        # Generate strong password
        $password = [System.Web.Security.Membership]::GeneratePassword(16, 2) + "Az1!"

        # Create user
        New-MsolUser `
            -DisplayName $account.Name `
            -UserPrincipalName $account.Username `
            -Password $password `
            -PasswordNeverExpires $false `
            -ForceChangePassword $true `
            -UsageLocation $Location

        Write-Host "✅ Account created: $($account.Username)" -ForegroundColor Green
        Write-Host "   Temporary password: $password" -ForegroundColor Yellow
        Write-Host "   ⚠️  User must change password on first login" -ForegroundColor Red

    } catch {
        Write-Host "❌ Failed to create $($account.Username): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n🏛️ Council 52 accounts creation complete!" -ForegroundColor Green
Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Assign Microsoft 365 licenses to new accounts"
Write-Host "   2. Grant mailbox permissions for consolidated access"
Write-Host "   3. Configure API access in Azure portal"
Write-Host "   4. Test account access and functionality"

Write-Host "`n🔐 Save these passwords securely and share with authorized personnel only!" -ForegroundColor Red