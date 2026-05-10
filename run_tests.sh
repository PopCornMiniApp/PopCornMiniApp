#!/bin/bash

# PopCorn Mini App - Test and Deployment Runner
# This script provides an easy interface to run the comprehensive test suite

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
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

# Function to show usage
show_usage() {
    cat << EOF
${GREEN}PopCorn Mini App - Test and Deployment Runner${NC}

Usage: $0 [OPTIONS]

OPTIONS:
    --dry-run           Run in dry-run mode (no actual changes)
    --test-only         Run tests only, skip deployment
    --deploy-only       Skip tests, deploy only
    --full              Run full test and deployment suite
    --component NAME    Test/deploy specific component only
                        (pre-deployment, hf-spaces, telegram-sync, frontend-sync, integration)
    --help              Show this help message

EXAMPLES:
    # Run full test suite in dry-run mode
    $0 --dry-run --full

    # Run tests only (no deployment)
    $0 --test-only

    # Test only HuggingFace Spaces
    $0 --test-only --component hf-spaces

    # Deploy only (skip tests)
    $0 --deploy-only

    # Full test and deployment
    $0 --full

ENVIRONMENT VARIABLES:
    The following environment variables should be set:
    - HF_TOKEN_1, HF_TOKEN_2
    - MAIN_BOT_TOKEN
    - STREAM_BOT_1, STREAM_BOT_2
    - Popcornapp1bot, Str_10bot
    - SESSION_1_API_ID, SESSION_1_API_HASH
    - SESSION_2_API_ID, SESSION_2_API_HASH
    - ADMIN_ID, ADMIN_USERNAME
    - PRIVATE_GROUPE_1_ID through Group private 8
    - PUBLIC_CHANNEL_ID
    - TMDB_API_KEY

EOF
}

# Function to check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_info "Using Python $PYTHON_VERSION"
}

# Function to check required files
check_files() {
    print_info "Checking required files..."
    
    REQUIRED_FILES=(
        "test_and_deploy_all.py"
        "fix_hf_spaces_build.py"
        "fix_telegram_sync_complete.py"
        "sync_db_to_frontend.py"
        "verify_frontend_sync.py"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Required file not found: $file"
            exit 1
        fi
    done
    
    print_success "All required files present"
}

# Function to check environment variables
check_env_vars() {
    print_info "Checking critical environment variables..."
    
    CRITICAL_VARS=(
        "HF_TOKEN_1"
        "MAIN_BOT_TOKEN"
        "ADMIN_ID"
    )
    
    MISSING_VARS=()
    for var in "${CRITICAL_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        print_warning "Missing critical environment variables: ${MISSING_VARS[*]}"
        print_warning "Some tests may fail. Continue? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Aborted by user"
            exit 0
        fi
    else
        print_success "Critical environment variables are set"
    fi
}

# Function to create backup
create_backup() {
    print_info "Creating backup before deployment..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup critical files
    cp -r app "$BACKUP_DIR/" 2>/dev/null || true
    cp -r frontend/src/*.json "$BACKUP_DIR/" 2>/dev/null || true
    
    print_success "Backup created at: $BACKUP_DIR"
}

# Function to run tests
run_tests() {
    print_info "Starting test and deployment suite..."
    echo ""
    
    # Build Python command
    PYTHON_CMD="python3 test_and_deploy_all.py"
    
    # Add arguments
    for arg in "$@"; do
        PYTHON_CMD="$PYTHON_CMD $arg"
    done
    
    print_info "Executing: $PYTHON_CMD"
    echo ""
    
    # Run the Python script
    if $PYTHON_CMD; then
        print_success "Test and deployment completed successfully!"
        return 0
    else
        print_error "Test and deployment failed!"
        return 1
    fi
}

# Function to show results
show_results() {
    echo ""
    print_info "Test Results:"
    
    if [ -f "test_deploy_report.json" ]; then
        # Extract summary from JSON report
        python3 << EOF
import json
try:
    with open('test_deploy_report.json', 'r') as f:
        report = json.load(f)
    
    summary = report['summary']
    print(f"\n📊 Summary:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Duration: {summary['duration_seconds']:.2f} seconds")
    print(f"\n📈 Status Breakdown:")
    for status, count in summary['status_counts'].items():
        emoji = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️', 'WARN': '⚠️'}
        print(f"   {emoji.get(status, '❓')} {status}: {count}")
except Exception as e:
    print(f"Error reading report: {e}")
EOF
    fi
    
    if [ -f "TEST_DEPLOY_REPORT.md" ]; then
        print_info "Detailed report available at: TEST_DEPLOY_REPORT.md"
    fi
    
    if [ -f "test_deploy.log" ]; then
        print_info "Full log available at: test_deploy.log"
    fi
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     PopCorn Mini App - Test & Deployment Runner           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Parse arguments
    if [ $# -eq 0 ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
        show_usage
        exit 0
    fi
    
    # Pre-flight checks
    check_python
    check_files
    check_env_vars
    
    # Create backup if not in dry-run mode
    if [[ ! "$*" =~ "--dry-run" ]] && [[ ! "$*" =~ "--test-only" ]]; then
        create_backup
    fi
    
    # Run tests
    if run_tests "$@"; then
        show_results
        exit 0
    else
        show_results
        print_error "Tests failed. Check logs for details."
        exit 1
    fi
}

# Run main function
main "$@"

# Made with Bob
