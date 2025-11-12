# Fix Backend Connection - Run as Administrator
# This script opens Windows Firewall port 8000 for the backend

Write-Host "Opening Windows Firewall for port 8000..." -ForegroundColor Yellow

# Add inbound rule for port 8000
netsh advfirewall firewall add rule name="Python Backend Port 8000" dir=in action=allow protocol=TCP localport=8000

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Firewall rule added successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Backend should now be accessible on:" -ForegroundColor Cyan
    Write-Host "  - http://127.0.0.1:8000 (localhost)" -ForegroundColor White
    Write-Host "  - http://192.168.36.34:8000 (LAN IP)" -ForegroundColor White
    Write-Host ""
    Write-Host "If you need a different IP, check with: ipconfig" -ForegroundColor Yellow
} else {
    Write-Host "✗ Failed to add firewall rule. Make sure you're running as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To fix manually:" -ForegroundColor Yellow
    Write-Host "1. Open Windows Defender Firewall" -ForegroundColor White
    Write-Host "2. Click 'Advanced settings'" -ForegroundColor White
    Write-Host "3. Click 'Inbound Rules' > 'New Rule'" -ForegroundColor White
    Write-Host "4. Select 'Port' > 'TCP' > 'Specific local ports: 8000'" -ForegroundColor White
    Write-Host "5. Allow the connection" -ForegroundColor White
}

