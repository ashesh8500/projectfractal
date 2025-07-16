#!/bin/bash
set -e

# Configuration
GCP_PROJECT_ID="projectfractal"
GCS_BUCKET="portfolio-optimizer-frontend"
REGION="us-central1"
BACKEND_URL="https://portfolio-backend-abcdefghij-uc.a.run.app"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "You need to log in to Google Cloud first. Run 'gcloud auth login'."
    exit 1
fi

# Build the WASM version
echo "Building WASM version..."
./build_wasm.sh

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "Build failed. Aborting deployment."
    exit 1
fi

# Create GCS bucket if it doesn't exist
if ! gcloud storage buckets describe gs://${GCS_BUCKET} &> /dev/null; then
    echo "Creating GCS bucket: ${GCS_BUCKET}"
    gcloud storage buckets create gs://${GCS_BUCKET} --location=${REGION} --project=${GCP_PROJECT_ID}
    
    # Set public access
    echo "Setting bucket to public access..."
    gcloud storage buckets add-iam-policy-binding gs://${GCS_BUCKET} \
        --member=allUsers --role=roles/storage.objectViewer
fi

# Upload files to GCS
echo "Uploading files to GCS bucket..."
gcloud storage cp -r dist/* gs://${GCS_BUCKET}/

# Configure website settings
echo "Configuring website settings..."
cat > website-config.json << EOL
{
  "mainPageSuffix": "index.html",
  "notFoundPage": "index.html"
}
EOL

gcloud storage buckets update gs://${GCS_BUCKET} --website-main-page-suffix=index.html --website-error-page=index.html

# Set CORS configuration
echo "Setting CORS configuration..."
cat > cors-config.json << EOL
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD", "OPTIONS"],
    "responseHeader": ["Content-Type", "Access-Control-Allow-Origin"],
    "maxAgeSeconds": 3600
  }
]
EOL

gcloud storage buckets update gs://${GCS_BUCKET} --cors-file=cors-config.json

# Clean up temporary files
rm website-config.json cors-config.json

# Create Load Balancer (optional)
# This is a simplified version. For production, you might want to set up SSL, CDN, etc.
echo "Do you want to set up a Load Balancer with a custom domain? (y/n)"
read -r setup_lb

if [[ "$setup_lb" == "y" ]]; then
    echo "Enter your domain name (e.g., portfolio.example.com):"
    read -r domain_name
    
    # Create backend bucket
    gcloud compute backend-buckets create ${GCS_BUCKET}-backend \
        --gcs-bucket-name=${GCS_BUCKET} \
        --enable-cdn
    
    # Create URL map
    gcloud compute url-maps create ${GCS_BUCKET}-url-map \
        --default-backend-bucket=${GCS_BUCKET}-backend
    
    # Create HTTP proxy
    gcloud compute target-http-proxies create ${GCS_BUCKET}-http-proxy \
        --url-map=${GCS_BUCKET}-url-map
    
    # Create forwarding rule
    gcloud compute forwarding-rules create ${GCS_BUCKET}-http \
        --target-http-proxy=${GCS_BUCKET}-http-proxy \
        --global \
        --ports=80
    
    echo "Load Balancer set up complete."
    echo "Now you need to configure your DNS to point ${domain_name} to the Load Balancer IP."
    echo "You can find the IP address with: gcloud compute forwarding-rules describe ${GCS_BUCKET}-http --global"
fi

echo "Deployment complete!"
echo "Your application is available at: https://storage.googleapis.com/${GCS_BUCKET}/index.html"
if [[ "$setup_lb" == "y" ]]; then
    echo "Once DNS propagates, it will also be available at: http://${domain_name}"
fi