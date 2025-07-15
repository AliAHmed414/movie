#!/bin/bash

echo "🔧 Updating system packages..."
sudo apt update
sudo apt --fix-broken install
sudo apt upgrade -y

echo "📦 Installing core system tools..."
sudo apt install -y python3 python3-pip ffmpeg libffi-dev libssl-dev build-essential python3-libtorrent

# echo "🌐 Installing Microsoft Edge..."
# curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
# sudo install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/
# sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list'
# sudo apt update
# sudo apt install -y microsoft-edge-stable

echo "🌍 Installing Google Chrome..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb || sudo apt install -f -y  # Fix dependencies if needed

echo "🐍 Upgrading pip and installing Python packages..."
pip3 install --upgrade pip

pip3 install Flask aiohttp langdetect undetected_chromedriver selenium libtorrent subliminal babelfish

echo "🧠 Installing Google Generative AI SDK..."
pip3 install -q -U google-genai

echo "✅ All dependencies installed!"
echo "🎞️  ffmpeg version: $(ffmpeg -version | head -n 1)"
echo "🧲 libtorrent version: $(python3 -c 'import libtorrent as lt; print(lt.version)' 2>/dev/null || echo "libtorrent not found")"