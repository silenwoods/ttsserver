# TTS Server HTTPS Deployment Guide (use_https branch)

## Prerequisites
- Python 3.8+ (Python 3.13 recommended)
- pip (Python package manager)
- espeak (for /3 endpoint)
- git (optional)
- OpenSSL (for certificate generation)

## Installation Steps

### 1. Clone or Copy Files
```bash
# Clone the use_https branch
git clone -b use_https <repository-url>

# OR copy files manually
mkdir ttsserver-https
cd ttsserver-https
# copy app.py, requirements.txt, pyproject.toml, cert.pem, key.pem here
```

### 2. Install System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install espeak python3-pip python3-venv openssl

# CentOS/RHEL/Fedora
sudo yum install espeak python3-pip openssl
# OR for newer systems
sudo dnf install espeak python3-pip openssl

# macOS
brew install espeak openssl
```

### 3. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5. SSL Certificate Setup

#### Option A: Use existing certificates (if provided)
Ensure `cert.pem` and `key.pem` are in the same directory as app.py.

#### Option B: Generate self-signed certificates
```bash
# Generate private key
openssl genrsa -out key.pem 4096

# Generate certificate signing request
openssl req -new -key key.pem -out cert.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate (valid for 10 years)
openssl x509 -req -in cert.csr -signkey key.pem -out cert.pem -days 3650

# Clean up CSR (optional)
rm cert.csr
```

#### Option C: Use Let's Encrypt (for production)
```bash
# Install certbot
sudo apt install certbot  # Ubuntu/Debian
sudo yum install certbot  # CentOS/RHEL

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to app directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem key.pem
sudo chown $USER:$USER cert.pem key.pem
```

### 6. Test Installation
```bash
python -c "import pyttsx3; import gtts; import ssl; print('All dependencies installed successfully')"
```

### 7. Run the HTTPS Server

#### Development Mode
```bash
# Start HTTPS server on port 5000
python app.py
```

#### Production Mode (recommended)
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn over HTTPS
gunicorn -w 4 -b 0.0.0.0:5000 --certfile=cert.pem --keyfile=key.pem app:create_app()

# Or with systemd service (see below)
```

## Port Configuration
- Default HTTPS port: 5000 (not 443 - change for production)
- To change port: Edit `app.run(port=NEW_PORT)` in app.py
- Ensure firewall allows the port:
  ```bash
  # Ubuntu/Debian with ufw
  sudo ufw allow 5000

  # CentOS/RHEL with firewalld
  sudo firewall-cmd --permanent --add-port=5000/tcp
  sudo firewall-cmd --reload
  ```

## Environment Variables
```bash
# Set production mode
export FLASK_ENV=production

# Custom port
export PORT=5000

# Custom certificate paths
export CERT_PATH=./cert.pem
export KEY_PATH=./key.pem
```

## Production HTTPS Configuration

### nginx + gunicorn setup
```nginx
# /etc/nginx/sites-available/ttsserver
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### systemd service
```ini
# /etc/systemd/system/ttsserver.service
[Unit]
Description=TTS Server HTTPS
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ttsserver-https
Environment="PATH=/path/to/ttsserver-https/.venv/bin"
ExecStart=/path/to/ttsserver-https/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --certfile=cert.pem --keyfile=key.pem app:create_app()
Restart=always

[Install]
WantedBy=multi-user.target
```

## Docker HTTPS Deployment

### Dockerfile
```dockerfile
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    espeak \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and certificates
COPY app.py .
COPY cert.pem key.pem ./

# Expose HTTPS port
EXPOSE 5000

# Run the application with HTTPS
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--certfile=cert.pem", "--keyfile=key.pem", "app:create_app()"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  ttsserver-https:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./cert.pem:/app/cert.pem:ro
      - ./key.pem:/app/key.pem:ro
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

## Testing HTTPS Endpoints

### Test self-signed certificates
```bash
# Skip certificate verification for testing
curl -k "https://localhost:5000/1?text=Hello+World" -o test1.mp3
curl -k "https://localhost:5000/2?text=Hello+World" -o test2.wav
curl -k "https://localhost:5000/3?text=Hello+World" -o test3.wav

# Test with proper certificates
curl "https://yourdomain.com:5000/1?text=Hello+World" -o test1.mp3
```

### Browser testing
- Visit `https://your-server:5000/1?text=Hello` to test gTTS endpoint
- Accept certificate warning if using self-signed certificates

## Troubleshooting HTTPS Issues

### Common SSL Errors:
1. **SSL: CERTIFICATE_VERIFY_FAILED**: Use valid certificates or add `-k` flag to curl
2. **Port 443 permission denied**: Use `sudo` or change to higher port
3. **Certificate expired**: Regenerate certificates
4. **Wrong domain in certificate**: Regenerate with correct CN

### Debug SSL connection
```bash
# Test SSL handshake
openssl s_client -connect localhost:5000

# Check certificate details
openssl x509 -in cert.pem -text -noout

# Test with verbose output
curl -v -k "https://localhost:5000/1?text=test"
```

### Certificate validation
```bash
# Verify certificate and key match
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
# The MD5 hashes should match
```

## Security Considerations
- Use Let's Encrypt certificates for production
- Keep private key secure (chmod 600 key.pem)
- Use strong cipher suites
- Implement proper rate limiting
- Consider using a reverse proxy for additional security
- Monitor SSL/TLS vulnerabilities
- Regular certificate renewal (Let's Encrypt: 90 days)

## Performance Tuning
- Use nginx for SSL termination
- Enable HTTP/2
- Configure SSL session caching
- Use OCSP stapling
- Implement proper load balancing for multiple instances