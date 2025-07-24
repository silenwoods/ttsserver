# TTS Server Deployment Guide

## Prerequisites
- Python 3.8+ (Python 3.13 recommended)
- pip (Python package manager)
- espeak (for /3 endpoint)
- git (optional)

## Installation Steps

### 1. Clone or Copy Files
```bash
# Clone from git
git clone <repository-url>

# OR copy files manually
mkdir ttsserver
cd ttsserver
# copy app.py, requirements.txt, pyproject.toml here
```

### 2. Install System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install espeak python3-pip python3-venv

# CentOS/RHEL/Fedora
sudo yum install espeak python3-pip
# OR for newer systems
sudo dnf install espeak python3-pip

# macOS
brew install espeak
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

### 5. Test Installation
```bash
python -c "import pyttsx3; import gtts; print('All dependencies installed successfully')"
```

### 6. Run the Server
```bash
# Development mode
python app.py

# Production mode (recommended)
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:create_app()
```

## Port Configuration
- Default port: 5000
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
You can set these optional environment variables:
- `FLASK_ENV=production` - Disable debug mode
- `PORT=5000` - Set custom port

## Docker Deployment (Optional)
```dockerfile
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    espeak \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
```

## Testing Endpoints
```bash
# Test each endpoint
curl "http://localhost:5000/1?text=Hello+World" -o test1.mp3
curl "http://localhost:5000/2?text=Hello+World" -o test2.wav
curl "http://localhost:5000/3?text=Hello+World" -o test3.wav

# Check if files are generated
ls -la test*.mp3 test*.wav
```

## Troubleshooting

### Common Issues:
1. **Port already in use**: Change port or kill process using `lsof -i :5000`
2. **espeak not found**: Install espeak system package
3. **Permission denied**: Use `sudo` for port <1024 or change to higher port
4. **CORS issues**: Already configured in app.py with flask-cors

### Debug Mode
```bash
# Enable debug logging
python app.py
# Check console output for detailed errors
```

## Production Considerations
- Use a reverse proxy (nginx, apache)
- Set up SSL certificates
- Configure rate limiting storage backend
- Monitor resource usage
- Set up log rotation
- Use process manager (systemd, supervisor)