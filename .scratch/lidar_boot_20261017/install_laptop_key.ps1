# One-time: add this laptop's public key to pi5@192.168.0.101, so later SSH
# needs no password. Pinned to the user-confirmed host key (SHA256:hb9hOhko...).
# ssh splits -o values at spaces, so the pinned copy lives on a space-free path.
$knownHosts = Join-Path $env:TEMP 'aerothon_pi_known_hosts'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'pi_known_hosts') -Destination $knownHosts -Force
$publicKey = (Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" -Raw).Trim()
$remote = 'umask 077; mkdir -p ~/.ssh; read -r k; grep -qxF "$k" ~/.ssh/authorized_keys 2>/dev/null || echo "$k" >> ~/.ssh/authorized_keys; echo KEY INSTALLED'
$publicKey | ssh -o UserKnownHostsFile="$knownHosts" -o StrictHostKeyChecking=yes pi5@192.168.0.101 $remote
