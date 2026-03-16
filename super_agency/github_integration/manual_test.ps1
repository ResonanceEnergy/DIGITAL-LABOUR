# Manual GitHub Authentication Test
# Run this in PowerShell or Command Prompt

Write-Host "🔐 Manual GitHub Authentication Test" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Yellow

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✅ .env file found" -ForegroundColor Green

    # Read the token
    $envContent = Get-Content ".env" -Raw
    $tokenLine = $envContent -split "`n" | Where-Object { $_ -match "^GITHUB_TOKEN=" }
    if ($tokenLine) {
        $token = ($tokenLine -split "=", 2)[1].Trim()
        if ($token -and $token -ne "your_personal_access_token_here") {
            Write-Host "✅ Token found in .env file" -ForegroundColor Green

            # Test the token manually
            Write-Host "`n🔍 Testing GitHub API connection..." -ForegroundColor Yellow

            try {
                $headers = @{
                    "Authorization" = "token $token"
                    "Accept" = "application/vnd.github.v3+json"
                }

                # Test user endpoint
                $userResponse = Invoke-WebRequest -Uri "https://api.github.com/user" -Headers $headers -Method GET -UseBasicParsing
                if ($userResponse.StatusCode -eq 200) {
                    $userData = $userResponse.Content | ConvertFrom-Json
                    Write-Host "✅ GitHub API connection successful!" -ForegroundColor Green
                    Write-Host "   Authenticated as: $($userData.login)" -ForegroundColor Green

                    # Test organization access
                    try {
                        $orgResponse = Invoke-WebRequest -Uri "https://api.github.com/orgs/ResonanceEnergy" -Headers $headers -Method GET -UseBasicParsing
                        if ($orgResponse.StatusCode -eq 200) {
                            $orgData = $orgResponse.Content | ConvertFrom-Json
                            Write-Host "✅ Organization access confirmed!" -ForegroundColor Green
                            Write-Host "   Organization: $($orgData.name)" -ForegroundColor Green
                        } else {
                            Write-Host "❌ Organization access failed: $($orgResponse.StatusCode)" -ForegroundColor Red
                        }
                    } catch {
                        Write-Host "❌ Organization access error: $($_.Exception.Message)" -ForegroundColor Red
                    }

                } else {
                    Write-Host "❌ API connection failed: $($userResponse.StatusCode)" -ForegroundColor Red
                }

            } catch {
                Write-Host "❌ Connection error: $($_.Exception.Message)" -ForegroundColor Red
            }

        } else {
            Write-Host "❌ Token is placeholder value" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ GITHUB_TOKEN not found in .env" -ForegroundColor Red
    }
} else {
    Write-Host "❌ .env file not found" -ForegroundColor Red
}

Write-Host "`n=====================================" -ForegroundColor Yellow
Write-Host "🎯 If successful, run: .\run_github_integration.bat sync" -ForegroundColor Cyan