# Authorise this laptop's SSH key on the Pi: copy_ssh_key.ps1 [ip]
# The Pi asks for pi5's password once; type it here.
param([string]$PiIp = '192.168.137.148')
$pub = Join-Path $env:USERPROFILE '.ssh\id_ed25519.pub'
Get-Content $pub | ssh -o StrictHostKeyChecking=yes "pi5@$PiIp" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo KEY INSTALLED"
