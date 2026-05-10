#!/bin/bash

# Quick Start Script for HuggingFace Spaces Build Fix
# This script provides an easy way to run the fix with common options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     HuggingFace Spaces Build Fix - Quick Start Script         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo ""
    echo "Please create a .env file with your HuggingFace tokens:"
    echo ""
    echo "  HF_TOKEN_1=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    echo "  HF_TOKEN_2=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    echo ""
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 not found${NC}"
    exit 1
fi

# Check if required packages are installed
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
python3 -c "import huggingface_hub, dotenv, requests" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Missing dependencies. Installing...${NC}"
    pip install huggingface-hub python-dotenv requests
}

echo -e "${GREEN}✅ Dependencies OK${NC}"
echo ""

# Show menu
echo -e "${BLUE}Select an option:${NC}"
echo ""
echo "  1) Fix all Spaces (Full diagnosis + fixes)"
echo "  2) Monitor status only (no changes)"
echo "  3) Fix specific Spaces"
echo "  4) Quick fix (skip diagnosis)"
echo "  5) Show help"
echo "  6) Exit"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}🚀 Starting full fix for all Spaces...${NC}"
        echo -e "${YELLOW}⏱️  This will take 35-75 minutes${NC}"
        echo ""
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            python3 fix_hf_spaces_build.py
        else
            echo "Cancelled."
        fi
        ;;
    2)
        echo ""
        echo -e "${GREEN}🔍 Checking Space status...${NC}"
        echo ""
        python3 fix_hf_spaces_build.py --monitor-only
        ;;
    3)
        echo ""
        echo -e "${BLUE}Available Spaces:${NC}"
        echo "  1) PopCorn (Main)"
        echo "  2) popcorn-main"
        echo "  3) popcorn-streaming"
        echo "  4) popcorn-backup"
        echo "  5) popcorn-analytics"
        echo ""
        read -p "Enter space numbers (e.g., 1 2 3): " spaces
        
        space_names=""
        for num in $spaces; do
            case $num in
                1) space_names="$space_names ToolKit-backend/PopCorn" ;;
                2) space_names="$space_names popcorn-main" ;;
                3) space_names="$space_names popcorn-streaming" ;;
                4) space_names="$space_names popcorn-backup" ;;
                5) space_names="$space_names popcorn-analytics" ;;
            esac
        done
        
        if [ -n "$space_names" ]; then
            echo ""
            echo -e "${GREEN}🚀 Fixing selected Spaces...${NC}"
            python3 fix_hf_spaces_build.py --spaces $space_names
        else
            echo -e "${RED}❌ No valid spaces selected${NC}"
        fi
        ;;
    4)
        echo ""
        echo -e "${YELLOW}⚠️  Quick fix mode (skips diagnosis)${NC}"
        echo "This will apply all fixes without checking what's needed."
        echo ""
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            python3 fix_hf_spaces_build.py --skip-diagnosis
        else
            echo "Cancelled."
        fi
        ;;
    5)
        echo ""
        python3 fix_hf_spaces_build.py --help
        echo ""
        echo -e "${BLUE}📖 For detailed documentation, see:${NC}"
        echo "   HF_SPACES_BUILD_FIX_GUIDE.md"
        ;;
    6)
        echo ""
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Done!${NC}"
echo ""
echo -e "${BLUE}📊 Check the generated log file for detailed results${NC}"
echo -e "${BLUE}📖 See HF_SPACES_BUILD_FIX_GUIDE.md for more information${NC}"
echo ""

# Made with Bob
