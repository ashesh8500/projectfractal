#!/bin/bash
set -e

# Configuration - Edit these variables as needed
GCP_PROJECT_ID="projectfractal"
GCS_BUCKET="portfolio-optimizer-frontend"
REGION="us-central1"
BACKEND_URL="https://portfolio-backend-abcdefghij-uc.a.run.app"
DOMAIN_NAME="" # Leave empty if you don't have a custom domain

# Advanced configuration
ENABLE_CDN=true
ENABLE_SSL=true
ENABLE_COMPRESSION=true
CACHE_CONTROL_MAX_AGE=3600 # 1 hour for HTML files
CACHE_CONTROL_MAX_AGE_ASSETS=604800 # 1 week for static assets

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_warning "You need to log in to Google Cloud first."
    gcloud auth login
fi

# Set the GCP project
print_status "Setting GCP project to ${GCP_PROJECT_ID}..."
gcloud config set project ${GCP_PROJECT_ID}

# Enable required APIs
print_status "Enabling required GCP APIs..."
gcloud services enable storage-api.googleapis.com compute.googleapis.com

# Build the WASM version
print_status "Building WASM version..."
./build_wasm.sh

# Check if build was successful
if [ $? -ne 0 ]; then
    print_error "Build failed. Aborting deployment."
    exit 1
fi

# Update config.js with the correct backend URL
print_status "Updating configuration with backend URL: ${BACKEND_URL}"
sed -i "s|apiUrl: \".*\"|apiUrl: \"${BACKEND_URL}\"|" dist/config.js

# Create GCS bucket if it doesn't exist
if ! gcloud storage buckets describe gs://${GCS_BUCKET} &> /dev/null; then
    print_status "Creating GCS bucket: ${GCS_BUCKET}"
    gcloud storage buckets create gs://${GCS_BUCKET} --location=${REGION} --project=${GCP_PROJECT_ID}
    
    # Set public access
    print_status "Setting bucket to public access..."
    gcloud storage buckets add-iam-policy-binding gs://${GCS_BUCKET} \
        --member=allUsers --role=roles/storage.objectViewer
else
    print_status "Using existing bucket: ${GCS_BUCKET}"
fi

# Configure website settings
print_status "Configuring website settings..."
gcloud storage buckets update gs://${GCS_BUCKET} --website-main-page-suffix=index.html --website-error-page=index.html

# Set CORS configuration
print_status "Setting CORS configuration..."
cat > cors-config.json << EOL
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD", "OPTIONS"],
    "responseHeader": ["Content-Type", "Access-Control-Allow-Origin", "Cache-Control"],
    "maxAgeSeconds": 3600
  }
]
EOL

gcloud storage buckets update gs://${GCS_BUCKET} --cors-file=cors-config.json

# Upload files to GCS with appropriate cache settings
print_status "Uploading files to GCS bucket..."

# Upload HTML and config files with shorter cache time
print_status "Uploading HTML and configuration files..."
gcloud storage cp dist/index.html dist/config.js dist/version.json gs://${GCS_BUCKET}/ \
    --cache-control="public, max-age=${CACHE_CONTROL_MAX_AGE}" \
    --content-encoding=gzip

# Upload WASM and JS files with longer cache time
print_status "Uploading WASM and JavaScript files..."
gcloud storage cp dist/*.wasm dist/*.js gs://${GCS_BUCKET}/ \
    --cache-control="public, max-age=${CACHE_CONTROL_MAX_AGE_ASSETS}" \
    --content-encoding=gzip

# Clean up temporary files
rm -f cors-config.json

# Set up Load Balancer if domain name is provided
if [[ -n "${DOMAIN_NAME}" ]]; then
    print_status "Setting up Load Balancer for domain: ${DOMAIN_NAME}"
    
    # Create backend bucket
    print_status "Creating backend bucket..."
    gcloud compute backend-buckets create ${GCS_BUCKET}-backend \
        --gcs-bucket-name=${GCS_BUCKET} \
        --enable-cdn=${ENABLE_CDN}
    
    # Create URL map
    print_status "Creating URL map..."
    gcloud compute url-maps create ${GCS_BUCKET}-url-map \
        --default-backend-bucket=${GCS_BUCKET}-backend
    
    # Set up SSL if enabled
    if [[ "${ENABLE_SSL}" == "true" ]]; then
        print_status "Setting up SSL certificate..."
        
        # Create SSL certificate
        gcloud compute ssl-certificates create ${GCS_BUCKET}-cert \
            --domains=${DOMAIN_NAME} \
            --global
        
        # Create HTTPS proxy
        gcloud compute target-https-proxies create ${GCS_BUCKET}-https-proxy \
            --url-map=${GCS_BUCKET}-url-map \
            --ssl-certificates=${GCS_BUCKET}-cert
        
        # Create HTTPS forwarding rule
        gcloud compute forwarding-rules create ${GCS_BUCKET}-https \
            --target-https-proxy=${GCS_BUCKET}-https-proxy \
            --global \
            --ports=443
        
        print_status "HTTPS Load Balancer set up complete."
    else
        # Create HTTP proxy
        print_status "Creating HTTP proxy..."
        gcloud compute target-http-proxies create ${GCS_BUCKET}-http-proxy \
            --url-map=${GCS_BUCKET}-url-map
        
        # Create HTTP forwarding rule
        gcloud compute forwarding-rules create ${GCS_BUCKET}-http \
            --target-http-proxy=${GCS_BUCKET}-http-proxy \
            --global \
            --ports=80
        
        print_status "HTTP Load Balancer set up complete."
    fi
    
    # Get the IP address
    if [[ "${ENABLE_SSL}" == "true" ]]; then
        IP_ADDRESS=$(gcloud compute forwarding-rules describe ${GCS_BUCKET}-https --global --format="value(IPAddress)")
    else
        IP_ADDRESS=$(gcloud compute forwarding-rules describe ${GCS_BUCKET}-http --global --format="value(IPAddress)")
    fi
    
    print_success "Load Balancer set up complete with IP address: ${IP_ADDRESS}"
    print_status "Now you need to configure your DNS to point ${DOMAIN_NAME} to this IP address."
    print_status "Add an A record for ${DOMAIN_NAME} pointing to ${IP_ADDRESS}"
    
    # Print access URLs
    if [[ "${ENABLE_SSL}" == "true" ]]; then
        print_success "Once DNS propagates, your application will be available at: https://${DOMAIN_NAME}"
    else
        print_success "Once DNS propagates, your application will be available at: http://${DOMAIN_NAME}"
    fi
else
    print_status "No domain name provided. Skipping Load Balancer setup."
    print_success "Your application is available at: https://storage.googleapis.com/${GCS_BUCKET}/index.html"
fi

# Print deployment summary
print_success "Deployment complete!"
print_status "Project: ${GCP_PROJECT_ID}"
print_status "Bucket: gs://${GCS_BUCKET}"
print_status "Region: ${REGION}"
print_status "Backend URL: ${BACKEND_URL}"

if [[ -n "${DOMAIN_NAME}" ]]; then
    print_status "Domain: ${DOMAIN_NAME}"
    print_status "CDN Enabled: ${ENABLE_CDN}"
    print_status "SSL Enabled: ${ENABLE_SSL}"
fi

print_success "Your application is now deployed and ready to use!"