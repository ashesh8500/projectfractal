#!/bin/bash

# Deploy the Portfolio Optimizer to Google Cloud Platform
echo "Deploying Portfolio Optimizer to GCP..."

# Set variables
PROJECT_ID="valuationappproject"
BACKEND_SERVICE="portfolio-backend"
FRONTEND_BUCKET="portfolio-frontend-$PROJECT_ID"
REGION="us-central1"

# Ensure the GCP project is set
gcloud config set project $PROJECT_ID

# Build the WASM frontend
echo "Building WASM frontend..."
cd frontend_rust
./build_wasm.sh
cd ..

# Check if the frontend build was successful
if [ ! -d "frontend_rust/dist" ]; then
    echo "Frontend build failed. Aborting deployment."
    exit 1
fi

# Create the Cloud Storage bucket if it doesn't exist
echo "Setting up Cloud Storage bucket for frontend..."
if ! gcloud storage buckets describe gs://$FRONTEND_BUCKET &> /dev/null; then
    echo "Creating bucket $FRONTEND_BUCKET..."
    gcloud storage buckets create gs://$FRONTEND_BUCKET \
        --location=$REGION \
        --website-main-page-suffix=index.html \
        --website-error-page=index.html \
        --uniform-bucket-level-access
fi

# Upload the frontend files
echo "Uploading frontend files to Cloud Storage..."
gcloud storage cp -r frontend_rust/dist/* gs://$FRONTEND_BUCKET

# Make the bucket publicly accessible
echo "Making bucket publicly accessible..."
gcloud storage buckets add-iam-policy-binding gs://$FRONTEND_BUCKET \
    --member=allUsers \
    --role=roles/storage.objectViewer

# Build and deploy the backend
echo "Building and deploying backend to Cloud Run..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE

# Deploy to Cloud Run
gcloud run deploy $BACKEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
    --platform managed \
    --region=$REGION \
    --allow-unauthenticated

# Get the backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --platform managed --region=$REGION --format="value(status.url)")
echo "Backend deployed at: $BACKEND_URL"

# Get the frontend URL
FRONTEND_URL="https://storage.googleapis.com/$FRONTEND_BUCKET/index.html"
echo "Frontend deployed at: $FRONTEND_URL"

echo "Deployment complete!"
echo "Next steps:"
echo "1. Set up a Load Balancer to route traffic between the frontend and backend"
echo "2. Configure a custom domain if needed"
echo "3. Set up SSL certificates for secure access"