#!/bin/bash
# Quick start script for MS1 Iter2 API

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  User & Profile Service (MS1) - Iter2 Quick Start      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "Detected OS: $OS"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION found"

# Determine use case
echo ""
echo "Select deployment mode:"
echo "1) In-memory (dev, no database)"
echo "2) Docker Compose (local MySQL)"
echo "3) Local MySQL (manual)"
echo ""
read -p "Enter choice [1-3]: " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "Starting in-memory version..."
        echo ""
        
        # Set up venv
        if [ ! -d "venv" ]; then
            echo "Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate
        if [ "$OS" = "windows" ]; then
            source venv/Scripts/activate
        else
            source venv/bin/activate
        fi
        
        # Install requirements
        echo "Installing dependencies..."
        pip install -q -r requirements.txt
        
        echo ""
        echo "✓ Setup complete!"
        echo ""
        echo "Starting API on http://localhost:8000"
        echo "Documentation: http://localhost:8000/docs"
        echo ""
        
        python main.py
        ;;
    
    2)
        echo ""
        echo "Starting with Docker Compose..."
        echo ""
        
        # Check Docker
        if ! command -v docker-compose &> /dev/null; then
            echo "❌ Docker Compose not found. Please install Docker Desktop"
            exit 1
        fi
        
        echo "✓ Docker Compose found"
        echo ""
        echo "Starting MySQL + API..."
        docker-compose up
        ;;
    
    3)
        echo ""
        echo "Local MySQL setup..."
        echo ""
        
        # Check MySQL
        if ! command -v mysql &> /dev/null; then
            echo "❌ MySQL client not found. Please install MySQL"
            exit 1
        fi
        
        echo "✓ MySQL client found"
        echo ""
        
        # Set up venv
        if [ ! -d "venv" ]; then
            echo "Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate
        if [ "$OS" = "windows" ]; then
            source venv/Scripts/activate
        else
            source venv/bin/activate
        fi
        
        # Install requirements
        echo "Installing dependencies..."
        pip install -q -r requirements.txt
        
        echo ""
        echo "MySQL setup required. Please provide:"
        read -p "MySQL host [localhost]: " DB_HOST
        DB_HOST=${DB_HOST:-localhost}
        
        read -p "MySQL port [3306]: " DB_PORT
        DB_PORT=${DB_PORT:-3306}
        
        read -p "MySQL root password: " DB_ROOT_PASS
        
        # Create database and user
        echo ""
        echo "Creating database and user..."
        
        mysql -h $DB_HOST -P $DB_PORT -u root -p"$DB_ROOT_PASS" << EOF
CREATE DATABASE IF NOT EXISTS ms1_db;
CREATE USER IF NOT EXISTS 'ms1_user'@'$DB_HOST' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON ms1_db.* TO 'ms1_user'@'$DB_HOST';
FLUSH PRIVILEGES;
EOF
        
        # Initialize schema
        echo "Initializing database schema..."
        export DB_HOST DB_PORT DB_USER=ms1_user DB_PASSWORD=password123 DB_NAME=ms1_db
        python schema.py seed
        
        echo ""
        echo "✓ Database setup complete!"
        echo ""
        echo "Starting API on http://localhost:8000"
        echo "Documentation: http://localhost:8000/docs"
        echo ""
        
        python main_db.py
        ;;
    
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
