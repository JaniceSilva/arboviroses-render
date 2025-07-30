#!/usr/bin/env python3
"""
Application entry point for AWS Elastic Beanstalk
Sistema de Predição de Arboviroses
"""

import os
import sys

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app as application

if __name__ == "__main__":
    # Para desenvolvimento local
    application.run(debug=False, host='0.0.0.0', port=5000)

