#!/bin/bash

# YouTube Channel Predictor - Virtual Environment Setup Script

echo "🚀 Setting up Python virtual environment..."

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
echo "📦 Upgrading pip..."
python3 -m pip install --upgrade pip

# 필수 패키지 설치
echo "📥 Installing required packages..."
python3 -m pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate, run:"
echo "  deactivate"
