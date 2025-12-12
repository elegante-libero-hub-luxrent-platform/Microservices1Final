#!/bin/bash
# Deploy script for User & Profile Service (MS1) on Cloud Compute

set -e

echo "=== MS1 Deployment Script ==="
echo "This script deploys MS1 to a Cloud Compute VM"
echo ""

# Configuration
VM_USER=${1:-ms1}
VM_HOST=${2:-localhost}
VM_KEY=${3:-~/.ssh/cloud-compute}
REPO_URL="https://github.com/your-org/microservices1-iter2.git"
DEPLOY_DIR="/opt/ms1-api"

echo "Configuration:"
echo "  VM User: $VM_USER"
echo "  VM Host: $VM_HOST"
echo "  Deploy Directory: $DEPLOY_DIR"
echo ""

# Step 1: Prepare VM
echo "Step 1: Preparing VM..."
ssh -i "$VM_KEY" "$VM_USER@$VM_HOST" << 'EOF'
  sudo apt-get update
  sudo apt-get install -y python3.11 python3.11-venv git mysql-client
  sudo useradd -m -s /bin/bash ms1 || true
  sudo mkdir -p /opt/ms1-api
  sudo chown ms1:ms1 /opt/ms1-api
EOF

# Step 2: Clone/Pull repository
echo "Step 2: Pulling latest code..."
ssh -i "$VM_KEY" "$VM_USER@$VM_HOST" << EOF
  cd $DEPLOY_DIR
  [ -d .git ] && git pull origin main || git clone $REPO_URL .
EOF

# Step 3: Set up Python virtual environment
echo "Step 3: Setting up Python environment..."
ssh -i "$VM_KEY" "$VM_USER@$VM_HOST" << EOF
  cd $DEPLOY_DIR
  python3.11 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
EOF

# Step 4: Initialize database
echo "Step 4: Initializing database..."
ssh -i "$VM_KEY" "$VM_USER@$VM_HOST" << 'EOF'
  cd /opt/ms1-api
  source venv/bin/activate
  python schema.py seed
EOF

# Step 5: Install systemd service
echo "Step 5: Installing systemd service..."
ssh -i "$VM_KEY" "$VM_USER@$VM_HOST" << EOF
  sudo cp $DEPLOY_DIR/deployment/ms1-api.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable ms1-api
  sudo systemctl restart ms1-api
EOF

# Step 6: Verify deployment
echo "Step 6: Verifying deployment..."
ssh -i "$VM_KEY" "$VM_USER@$VM_HOST" "sudo systemctl status ms1-api"

echo ""
echo "=== Deployment Complete ==="
echo "Service is running at http://$VM_HOST:8000"
echo "API docs: http://$VM_HOST:8000/docs"
echo "Health check: http://$VM_HOST:8000/health"
echo ""
echo "Useful commands:"
echo "  Check status: sudo systemctl status ms1-api"
echo "  View logs: sudo journalctl -u ms1-api -f"
echo "  Restart service: sudo systemctl restart ms1-api"
