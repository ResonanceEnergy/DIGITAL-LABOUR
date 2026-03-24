# Test GitHub Authentication Manually

Write-Host "🔐 Testing GitHub Authentication for Bit Rage Systems" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Yellow

# Change to the github_integration directory
Set-Location "$PSScriptRoot\github_integration"

# Load environment variables
if (Test-Path ".env") {
    Write-Host "✅ Found .env file" -ForegroundColor Green

    # Read the token from .env file
    $envContent = Get-Content ".env" -Raw
    $tokenMatch = [regex]::Match($envContent, 'GITHUB_TOKEN=(.+)')
    if ($tokenMatch.Success) {
        $token = $tokenMatch.Groups[1].Value.Trim()
        if ($token -and $token -ne "your_personal_access_token_here") {
            Write-Host "✅ GitHub token found in .env" -ForegroundColor Green

            # Test authentication
            try {
                $headers = @{
                    "Authorization" = "token $token"
                    "Accept" = "application/vnd.github.v3+json"
                }

                $response = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headers -Method Get
                Write-Host "✅ GitHub API connection successful" -ForegroundColor Green
                Write-Host "   Authenticated as: $($response.login)" -ForegroundColor Green

                # Test organization access
                try {
                    $orgResponse = Invoke-RestMethod -Uri "https://api.github.com/orgs/ResonanceEnergy" -Headers $headers -Method Get
                    Write-Host "✅ Organization access confirmed: $($orgResponse.name)" -ForegroundColor Green
                } catch {
                    Write-Host "❌ Organization access failed: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
                }

            } catch {
                Write-Host "❌ Authentication failed: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
            }

        } else {
            Write-Host "❌ Token is still placeholder value" -ForegroundColor Red
            Write-Host "   Please update .env file with your actual GitHub token" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Could not find GITHUB_TOKEN in .env" -ForegroundColor Red
    }

} else {
    Write-Host "❌ .env file not found" -ForegroundColor Red
}

Write-Host "==================================================" -ForegroundColor Yellow
Write-Host "🎯 Next Steps:" -ForegroundColor Cyan
Write-Host "1. If authentication works, run: .\run_github_integration.bat sync" -ForegroundColor White
Write-Host "2. Check GITHUB_AUTH_SETUP_GUIDE.md for detailed instructions" -ForegroundColor White