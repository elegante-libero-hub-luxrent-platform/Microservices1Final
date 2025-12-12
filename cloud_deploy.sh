#!/bin/bash

# Cloud Run Deployment Script for MS1 (User & Profile Service)
# Usage: bash cloud_deploy.sh [service-name] [region]

set -e

# Configuration
SERVICE_NAME="${1:-ms1-api}"
REGION="${2:-us-central1}"
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP project not set. Run 'gcloud config set project PROJECT_ID'"
    exit 1
fi

echo "🚀 Starting Cloud Run deployment..."
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   Project: $PROJECT_ID"

# Step 1: Build Docker image
echo ""
echo "📦 Step 1: Building Docker image..."
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --project $PROJECT_ID

# Step 2: Deploy to Cloud Run
echo ""
echo "🚀 Step 2: Deploying to Cloud Run..."

# Collect environment variables
echo ""
echo "📋 Enter database configuration:"
read -p "DB_HOST (Cloud SQL Public IP or socket): " DB_HOST
read -p "DB_USER (database user): " DB_USER
read -p "DB_NAME (database name): " DB_NAME
read -p "DB_PASSWORD_SECRET (Secret Manager secret name): " DB_PASSWORD_SECRET
read -p "GCP_PROJECT_ID: " GCP_PROJECT_ID

# Deploy
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars=\
GCP_PROJECT_ID=$GCP_PROJECT_ID,\
DB_HOST=$DB_HOST,\
DB_USER=$DB_USER,\
DB_NAME=$DB_NAME,\
DB_PASSWORD_SECRET=$DB_PASSWORD_SECRET,\
DB_PORT=3306,\
USE_SQLITE=false \
    --service-account=$SERVICE_NAME@$PROJECT_ID.iam.gserviceaccount.com \
    --project $PROJECT_ID

# Step 3: Get service URL
echo ""
echo "✅ Deployment complete!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📖 API Documentation: $SERVICE_URL/docs"
echo "❤️ Health Check: $SERVICE_URL/health"
echo ""
echo "📊 View logs:"
echo "   gcloud run logs read $SERVICE_NAME --region $REGION --limit 50"
