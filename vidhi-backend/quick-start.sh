#!/bin/bash
# VIDHI Backend Quick Start Script

echo "🚀 VIDHI Backend Quick Start"
echo "=============================="
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Python found: $(python --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your AWS credentials!"
    echo ""
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "⚠️  AWS CLI not found. Install it to create AWS resources."
    echo "   Download from: https://aws.amazon.com/cli/"
else
    echo "✅ AWS CLI found: $(aws --version)"
    
    # Check AWS credentials
    if aws sts get-caller-identity &> /dev/null; then
        echo "✅ AWS credentials configured"
    else
        echo "⚠️  AWS credentials not configured. Run: aws configure"
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your AWS credentials"
echo "2. Create AWS resources (see README.md)"
echo "3. Enable AWS Bedrock model access"
echo "4. Run: python app.py"
echo ""
echo "For detailed instructions, see README.md"
