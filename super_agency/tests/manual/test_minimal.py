#!/usr/bin/env python3
"""
Minimal Bit Rage Systems Test
Test basic Flask functionality
"""

from flask import Flask, jsonify
import sys
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Bit Rage Systems Test - Working!"

@app.route('/api/status')
def status():
    return jsonify({
        "status": "working",
        "platform": sys.platform,
        "python_version": sys.version
    })

if __name__ == '__main__':
    print("🚀 Starting minimal Bit Rage Systems test...")
    print("📍 Access at: http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)