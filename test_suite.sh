#!/bin/bash

# test_suite.sh - Complete testing suite for Grapnel Backend
# Usage: ./test_suite.sh [local|production] [url]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}=====================================${NC}"
    echo -e "${BLUE} $1 ${NC}"
    echo -e "${BLUE}=====================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Default values
MODE="local"
API_URL="http://localhost:8000"
PRODUCTION_URL="https://hack-kp-grapnel-backend.onrender.com"

# Parse arguments
if [ $# -gt 0 ]; then
    MODE=$1
fi

if [ $# -gt 1 ]; then
    if [ "$MODE" == "production" ]; then
        PRODUCTION_URL=$2
        API_URL=$PRODUCTION_URL
    else
        API_URL=$2
    fi
fi

print_header "Grapnel Backend Test Suite"
echo -e "Mode: ${YELLOW}$MODE${NC}"
echo -e "Target URL: ${YELLOW}$API_URL${NC}"
echo -e "Timestamp: ${YELLOW}$(date)${NC}"

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"
    
    # Check required Python packages
    echo "Checking Python packages..."
    python3 -c "import aiohttp, asyncio" 2>/dev/null || {
        print_warning "Installing required packages..."
        pip3 install aiohttp
    }
    print_success "Required packages available"
    
    # Check if API is accessible (only for local mode)
    if [ "$MODE" == "local" ]; then
        echo "Checking if local API is running..."
        if curl -f -s "${API_URL}/api/v1/health" > /dev/null; then
            print_success "Local API is responding"
        else
            print_error "Local API is not responding at $API_URL"
            print_warning "Make sure to start your API server first:"
            echo "  python run.py"
            exit 1
        fi
    fi
}

# Run basic connectivity test
test_connectivity() {
    print_header "Testing API Connectivity"

    echo "Testing basic connectivity..."

    # List of possible health endpoints with/without trailing slashes
    HEALTH_ENDPOINTS=(
        "/api/v1/health"
        "/api/v1/health/"
        "/health"
        "/health/"
        "/status"
        "/status/"
        "/api/status"
        "/api/status/"
        "/ready"
        "/ready/"
    )

    CONNECTED=false
    for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
        if curl -f -s -L -m 10 "${API_URL}${endpoint}" > /dev/null; then
            CONNECTED=true
            HEALTH_RESPONSE=$(curl -s -L "${API_URL}${endpoint}")
            DETECTED_HEALTH_ENDPOINT="$endpoint"
            print_success "API connectivity test passed at endpoint: ${endpoint}"
            echo "Health Response: $HEALTH_RESPONSE"
            break
        fi
    done

    if [ "$CONNECTED" = false ]; then
        print_error "API connectivity test failed"
        print_warning "Please check:"
        echo "  1. URL is correct: $API_URL"
        echo "  2. API server is running"
        echo "  3. Network connectivity"
        exit 1
    fi
}



# Run comprehensive API tests
run_api_tests() {
    print_header "Running Comprehensive API Tests"
    
    echo "Executing full test suite..."
    
    # Create temporary test script if it doesn't exist
    if [ ! -f "test_api.py" ]; then
        print_warning "test_api.py not found. Please ensure the API testing script is available."
        return 1
    fi
    
    # Run the comprehensive test suite
    if python3 test_api.py --url "$API_URL"; then
        print_success "API test suite completed successfully"
        return 0
    else
        print_error "API test suite failed"
        return 1
    fi
}

# Run performance tests
run_performance_tests() {
    print_header "Running Performance Tests"
    
    if [ ! -f "monitoring_tools.py" ]; then
        print_warning "monitoring_tools.py not found. Skipping performance tests."
        return 0
    fi
    
    echo "Running performance benchmark..."
    if python3 monitoring_tools.py --url "$API_URL" --mode benchmark --users 5; then
        print_success "Performance tests completed"
    else
        print_warning "Performance tests encountered issues"
    fi
}

# Run load tests (lighter version for production)
run_load_tests() {
    print_header "Running Load Tests"

    if [ "$MODE" == "production" ]; then
        print_warning "Running lighter load tests for production environment"
        echo "This will run a reduced load test to avoid impacting production"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Load tests skipped"
            return 0
        fi
    fi

    # Use detected health endpoint from connectivity test
    TARGET_ENDPOINT="${DETECTED_HEALTH_ENDPOINT:-/api/v1/health}"

    echo "Running simple load test (100 requests) to $TARGET_ENDPOINT..."

    TOTAL_REQUESTS=100
    SUCCESSFUL_REQUESTS=0
    FAILED_REQUESTS=0

    echo "Progress: [                    ] 0%"

    for ((i=1; i<=TOTAL_REQUESTS; i++)); do
        if curl -f -s -L -m 5 "${API_URL}${TARGET_ENDPOINT}" > /dev/null; then
            ((SUCCESSFUL_REQUESTS++))
        else
            ((FAILED_REQUESTS++))
        fi

        # Update progress
        PERCENT=$((i * 100 / TOTAL_REQUESTS))
        PROGRESS_BAR=""
        for ((j=1; j<=20; j++)); do
            if [ $((j * 5)) -le $PERCENT ]; then
                PROGRESS_BAR+="="
            else
                PROGRESS_BAR+=" "
            fi
        done
        printf "\rProgress: [%s] %d%%" "$PROGRESS_BAR" "$PERCENT"

        # Small delay to avoid overwhelming the server
        sleep 0.05
    done

    echo ""
    print_success "Load test completed"
    echo "  Total Requests: $TOTAL_REQUESTS"
    echo "  Successful: $SUCCESSFUL_REQUESTS"
    echo "  Failed: $FAILED_REQUESTS"
    echo "  Success Rate: $(( SUCCESSFUL_REQUESTS * 100 / TOTAL_REQUESTS ))%"
}


# Generate test report
generate_report() {
    print_header "Generating Test Report"
    
    REPORT_FILE="test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "Grapnel Backend Test Report"
        echo "=========================="
        echo "Generated: $(date)"
        echo "Mode: $MODE"
        echo "Target URL: $API_URL"
        echo ""
        
        echo "Test Results:"
        echo "============="
        
        # Check if API is responding
        if curl -f -s -m 5 "${API_URL}/api/v1/health" > /dev/null; then
            echo "✅ API Connectivity: PASSED"
        else
            echo "❌ API Connectivity: FAILED"
        fi
        
        # Basic endpoint tests
        echo ""
        echo "Endpoint Tests:"
        echo "==============="
        
        # Health endpoint
        if curl -f -s -m 5 "${API_URL}/api/v1/health" > /dev/null; then
            echo "✅ GET /api/v1/health: PASSED"
        else
            echo "❌ GET /api/v1/health: FAILED"
        fi
        
        # Ready endpoint
        if curl -f -s -m 5 "${API_URL}/api/v1/ready" > /dev/null; then
            echo "✅ GET /api/v1/ready: PASSED"
        else
            echo "❌ GET /api/v1/ready: FAILED"
        fi
        
        # Stats endpoint
        if curl -f -s -m 5 "${API_URL}/api/v1/hashes/stats" > /dev/null; then
            echo "✅ GET /api/v1/hashes/stats: PASSED"
        else
            echo "❌ GET /api/v1/hashes/stats: FAILED"
        fi
        
        echo ""
        echo "System Information:"
        echo "==================="
        echo "Hostname: $(hostname)"
        echo "OS: $(uname -s)"
        echo "Architecture: $(uname -m)"
        
        # Get system stats if available
        if command -v free &> /dev/null; then
            echo "Memory Usage:"
            free -h | head -2
        fi
        
        if command -v df &> /dev/null; then
            echo "Disk Usage:"
            df -h / | tail -1
        fi
        
        echo ""
        echo "API Response Examples:"
        echo "====================="
        
        # Get health response
        echo "Health Response:"
        curl -s -m 5 "${API_URL}/api/v1/health" 2>/dev/null | head -5 || echo "Failed to get health response"
        
        echo ""
        echo "Stats Response:"
        curl -s -m 5 "${API_URL}/api/v1/hashes/stats" 2>/dev/null | head -5 || echo "Failed to get stats response"
        
        echo ""
        echo "Test Completion Time: $(date)"
        echo "=========================="
        
    } > "$REPORT_FILE"
    
    print_success "Test report generated: $REPORT_FILE"
    
    # Display summary
    echo ""
    echo "Report Summary:"
    echo "==============="
    cat "$REPORT_FILE" | grep -E "(✅|❌|Total|Success Rate|Failed)" | head -10
}

# Cleanup function
cleanup() {
    print_header "Cleaning Up"
    
    # Remove temporary files if any
    if [ -f "temp_test_results.json" ]; then
        rm -f "temp_test_results.json"
        print_success "Temporary files cleaned up"
    fi
}

# Interactive mode for production testing
interactive_production_setup() {
    if [ "$MODE" == "production" ] && [ -z "$PRODUCTION_URL" ]; then
        print_header "Production Testing Setup"
        
        echo "You're about to test a production environment."
        echo "Please provide the production URL:"
        read -p "Production URL: " PRODUCTION_URL
        
        if [ -z "$PRODUCTION_URL" ]; then
            print_error "No URL provided. Exiting."
            exit 1
        fi
        
        API_URL="$PRODUCTION_URL"
        
        echo ""
        echo "Production Testing Guidelines:"
        echo "1. Tests will be run with reduced intensity"
        echo "2. Load tests will be limited to avoid impact"
        echo "3. Only read operations will be tested extensively"
        echo ""
        
        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Testing cancelled by user"
            exit 0
        fi
    fi
}

# Main execution flow
main() {
    # Set up signal handlers
    trap cleanup EXIT
    trap 'print_warning "Test interrupted by user"; exit 1' INT
    
    # Interactive setup for production
    interactive_production_setup
    
    # Run test sequence
    check_prerequisites
    test_connectivity
    
    # Run different test suites based on mode
    if [ "$MODE" == "production" ]; then
        print_header "Production Test Suite"
        print_warning "Running production-safe tests only"
        
        # Basic API tests
        run_api_tests
        
        # Light load test
        print_header "Light Load Testing"
        echo "Running minimal load test for production..."
        
        REQUESTS=10
        SUCCESS=0
        for ((i=1; i<=REQUESTS; i++)); do
            if curl -f -s -m 5 "${API_URL}/api/v1/health" > /dev/null; then
                ((SUCCESS++))
            fi
            printf "."
        done
        echo ""
        print_success "Light load test: $SUCCESS/$REQUESTS requests successful"
        
    else
        print_header "Full Test Suite"
        
        # Comprehensive tests for local/development
        run_api_tests
        run_performance_tests
        run_load_tests
    fi
    
    # Generate report
    generate_report
    
    print_header "Test Suite Complete"
    print_success "All tests have been executed"
    echo "Check the generated report for detailed results"
}

# Help function
show_help() {
    echo "Grapnel Backend Test Suite"
    echo "========================="
    echo ""
    echo "Usage: $0 [MODE] [URL]"
    echo ""
    echo "Modes:"
    echo "  local       - Test local development server (default)"
    echo "  production  - Test production deployment with safe tests"
    echo ""
    echo "Examples:"
    echo "  $0                                           # Test local server"
    echo "  $0 local http://localhost:8000               # Test specific local URL"
    echo "  $0 production https://your-app.onrender.com  # Test production"
    echo "  $0 production                                # Interactive production setup"
    echo ""
    echo "Options:"
    echo "  -h, --help  Show this help message"
    echo ""
}

# Check for help flag
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
    exit 0
fi

# Make script executable reminder
if [ ! -x "$0" ]; then
    print_warning "Script is not executable. Run: chmod +x $0"
fi

# Execute main function
main "$@"