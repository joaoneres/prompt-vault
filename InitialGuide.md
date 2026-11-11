# Course Environment

Everything on Ubuntu: Cursor, Docker Engine, uv, Python 3.13, NATS CLI 0.3.1, and Node.js 22.

## Cursor

```bash
curl -fsSL https://downloads.cursor.com/keys/anysphere.asc | gpg --dearmor | sudo tee /etc/apt/keyrings/cursor.gpg > /dev/null
echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/cursor.gpg] https://downloads.cursor.com/aptrepo stable main" | sudo tee /etc/apt/sources.list.d/cursor.list > /dev/null
sudo apt update
sudo apt install cursor
```

## Docker Engine

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
docker run hello-world
docker --version
docker compose version
```

## uv and Python 3.13

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
uv python install 3.13
uv run --python 3.13 python --version
```

## NATS CLI 0.3.1

```bash
sudo apt install -y unzip
mkdir -p ~/.local/bin
tmp=$(mktemp -d)
curl -fsSL -o "$tmp/nats.zip" https://github.com/nats-io/natscli/releases/download/v0.3.1/nats-0.3.1-linux-amd64.zip
unzip -o "$tmp/nats.zip" -d "$tmp"
install -m 0755 "$tmp/nats-0.3.1-linux-amd64/nats" ~/.local/bin/nats
rm -rf "$tmp"
source ~/.bashrc
nats --version
```

## Node.js 22

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
source ~/.bashrc
nvm install 22
node --version
npm --version
```

## Checklist

```bash
uv --version
uv run --python 3.13 python --version
nats --version
node --version
npm --version
docker --version
docker compose version
docker run hello-world
```
