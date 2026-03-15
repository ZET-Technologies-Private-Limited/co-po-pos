#!/bin/bash

#############################################################################
# CO-PO-PSO Mapping System - Automated Setup Script
# Complete production-grade setup with database initialization
#############################################################################

set -e  # Exit on any error

echo "========================================="
echo "CO-PO-PSO Mapping System Setup"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 1. Check Prerequisites
print_info "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3.10+ is not installed"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed"
    exit 1
fi
print_success "PostgreSQL found: $(psql --version)"

# 2. Navigate to backend directory
print_info "Navigating to backend directory..."
cd backend || exit 1
print_success "Backend directory ready"

# 3. Setup Python environment
print_info "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

source venv/bin/activate
print_success "Virtual environment activated"

# 4. Install dependencies
print_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Dependencies installed"

# 5. Create environment file
print_info "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success ".env file created"
    print_info "IMPORTANT: Edit .env with your database credentials"
else
    print_info ".env already exists"
fi

# 6. Get database connection details
read -p "PostgreSQL host (default: localhost): " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "PostgreSQL port (default: 5432): " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "PostgreSQL user (default: postgres): " DB_USER
DB_USER=${DB_USER:-postgres}

read -sp "PostgreSQL password: " DB_PASSWORD
echo ""

read -p "Database name (default: co_po_pso_db): " DB_NAME
DB_NAME=${DB_NAME:-co_po_pso_db}

# 7. Test database connection
print_info "Testing database connection..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT 1" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_success "Database connection successful"
else
    print_error "Could not connect to database. Please check your credentials."
    exit 1
fi

# 8. Create database if it doesn't exist
print_info "Creating database..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;"
print_success "Database ready: $DB_NAME"

# 9. Initialize database schema
print_info "Initializing database schema..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f ../scripts/01_init_database.sql > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_success "Database schema initialized"
else
    print_error "Failed to initialize database schema"
    exit 1
fi

# 10. Verify database tables
print_info "Verifying database tables..."
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
print_success "Database has $TABLE_COUNT tables"

# 11. Update .env file with database URL
print_info "Updating .env with database configuration..."
DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env
rm -f .env.bak
print_success ".env updated with database URL"

# 12. Create required directories
print_info "Creating required directories..."
mkdir -p logs
mkdir -p uploads
mkdir -p data/embeddings
print_success "Directories created"

# 13. Setup logging
print_info "Setting up logging..."
touch logs/app.log
chmod 644 logs/app.log
print_success "Logging configured"

# 14. Display setup summary
echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
print_success "Backend system setup completed successfully"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env and add your API keys:"
echo "   - OPENAI_API_KEY"
echo "   - PINECONE_API_KEY"
echo "   - SECRET_KEY (generate with: openssl rand -hex 32)"
echo ""
echo "2. Start the development server:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m uvicorn app.main:app --reload"
echo ""
echo "3. Access the application:"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   ReDoc: http://localhost:8000/redoc"
echo ""
echo "4. Test the API:"
echo "   curl http://localhost:8000/health"
echo ""
echo "========================================="
echo ""

print_info "Database Statistics:"
echo "   Host: $DB_HOST:$DB_PORT"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo "   Tables: $TABLE_COUNT"
echo ""

print_info "For production deployment, see PRODUCTION_DEPLOYMENT.md"
print_info "For API documentation, see README.md"
echo ""
