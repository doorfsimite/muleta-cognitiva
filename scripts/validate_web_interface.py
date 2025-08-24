#!/usr/bin/env python3
"""
Manual validation script for the enhanced web interface.
Tests browser loading, API connectivity, and feature functionality.
"""

import webbrowser
import subprocess
import time
import sys
import signal
import os
from pathlib import Path


def start_api_server():
    """Start the API server in the background."""
    try:
        print("🚀 Starting API server...")
        api_process = subprocess.Popen(
            ["uv", "run", "uvicorn", "src.api.main:app", "--host", "localhost", "--port", "8000"],
            cwd="/Users/davisimite/Documents/muleta-cognitiva",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)  # Wait for server to start
        print("✅ API server started on http://localhost:8000")
        return api_process
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None


def start_web_server():
    """Start the web server for the interface."""
    try:
        print("🌐 Starting web server...")
        web_process = subprocess.Popen(
            ["python3", "scripts/serve_web.py", "--port", "3000"],
            cwd="/Users/davisimite/Documents/muleta-cognitiva",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Wait for server to start
        print("✅ Web server started on http://localhost:3000")
        return web_process
    except Exception as e:
        print(f"❌ Failed to start web server: {e}")
        return None


def validate_html_structure():
    """Validate the HTML structure of index.html."""
    print("\n📋 Validating HTML structure...")
    
    html_path = Path("/Users/davisimite/Documents/muleta-cognitiva/index.html")
    if not html_path.exists():
        print("❌ index.html not found")
        return False
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for required elements
    required_elements = [
        'class="app-container"',
        'class="sidebar"',
        'class="main-content"',
        'class="nav-tabs"',
        'id="chart"',
        'id="learning-dashboard"',
        'id="argument-flows"',
        'id="assessments"',
        'id="reviewChart"',
        'id="cardTypeChart"',
        'id="argumentChart"',
        'id="assessmentChart"',
        'id="knowledgeGapChart"',
        'echarts.min.js'
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Missing HTML elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ HTML structure validation passed")
    return True


def validate_javascript_functions():
    """Validate presence of required JavaScript functions."""
    print("\n🔧 Validating JavaScript functions...")
    
    html_path = Path("/Users/davisimite/Documents/muleta-cognitiva/index.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_functions = [
        'function escapeHtml',
        'function changeGraphType',
        'function showTab',
        'function selectEntity',
        'function refreshData',
        'function loadVisualizationData',
        'function loadLearningDashboard',
        'function loadArgumentFlows',
        'function loadAssessments',
        'function makeForceOption',
        'function makeCircularOption',
        'function makeFlowchartOption',
        'function generateCards',
        'function createArgumentSequence'
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in content:
            missing_functions.append(func)
    
    if missing_functions:
        print("❌ Missing JavaScript functions:")
        for func in missing_functions:
            print(f"   - {func}")
        return False
    
    print("✅ JavaScript function validation passed")
    return True


def validate_css_classes():
    """Validate presence of required CSS classes."""
    print("\n🎨 Validating CSS classes...")
    
    html_path = Path("/Users/davisimite/Documents/muleta-cognitiva/index.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_classes = [
        '.app-container',
        '.sidebar',
        '.main-content',
        '.nav-tabs',
        '.nav-tab',
        '.tab-content',
        '.tab-pane',
        '.learning-dashboard',
        '.stats-grid',
        '.stat-card',
        '.chart-container',
        '.controls',
        '.entity-list',
        '.entity-item',
        '.status-indicator'
    ]
    
    missing_classes = []
    for css_class in required_classes:
        if css_class not in content:
            missing_classes.append(css_class)
    
    if missing_classes:
        print("❌ Missing CSS classes:")
        for css_class in missing_classes:
            print(f"   - {css_class}")
        return False
    
    print("✅ CSS class validation passed")
    return True


def test_api_connectivity():
    """Test API connectivity and basic endpoints."""
    print("\n🔌 Testing API connectivity...")
    
    try:
        import urllib.request
        import json
        
        # Test basic endpoints
        endpoints = [
            "/api/entities",
            "/api/visualization",
            "/api/statistics"
        ]
        
        base_url = "http://localhost:8000"
        
        for endpoint in endpoints:
            try:
                response = urllib.request.urlopen(f"{base_url}{endpoint}", timeout=5)
                if response.status in [200, 404]:  # 404 is OK for empty database
                    print(f"✅ {endpoint} - Status: {response.status}")
                else:
                    print(f"⚠️  {endpoint} - Status: {response.status}")
            except Exception as e:
                print(f"❌ {endpoint} - Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        return False


def open_browser():
    """Open the web interface in the default browser."""
    print("\n🌐 Opening web interface in browser...")
    
    url = "http://localhost:3000"
    
    try:
        webbrowser.open(url)
        print(f"✅ Browser opened to {url}")
        return True
    except Exception as e:
        print(f"❌ Failed to open browser: {e}")
        return False


def print_manual_test_checklist():
    """Print manual testing checklist for the user."""
    print("\n📝 MANUAL TESTING CHECKLIST")
    print("=" * 50)
    print("\n🔍 Visual Interface Tests:")
    print("   □ Page loads without errors")
    print("   □ All tabs are visible (Grafo, Dashboard, Fluxogramas, Avaliações)")
    print("   □ Sidebar displays controls and entity list")
    print("   □ Main content area shows charts")
    print("   □ API status indicator shows connection state")
    
    print("\n🎛️  Functionality Tests:")
    print("   □ Tab navigation works (click each tab)")
    print("   □ Graph type selector changes visualization")
    print("   □ Entity search filters the list")
    print("   □ Entity selection toggles correctly")
    print("   □ Refresh button updates data")
    print("   □ Export button downloads image")
    
    print("\n📊 Dashboard Tests:")
    print("   □ Statistics cards display numbers")
    print("   □ Review chart shows data")
    print("   □ Card type pie chart renders")
    print("   □ Learning metrics are visible")
    
    print("\n🔀 Flowchart Tests:")
    print("   □ Argument chart displays nodes")
    print("   □ Sequence creation form is functional")
    print("   □ Selected entities list updates")
    print("   □ Create sequence button is clickable")
    
    print("\n📈 Assessment Tests:")
    print("   □ Assessment history chart displays")
    print("   □ Knowledge gap radar chart renders")
    print("   □ Charts resize properly")
    
    print("\n📱 Responsive Tests:")
    print("   □ Interface adapts to different window sizes")
    print("   □ Mobile layout works on narrow screens")
    print("   □ All elements remain accessible")
    
    print("\n🎨 Visual Design Tests:")
    print("   □ Colors and styling look professional")
    print("   □ Charts use consistent color scheme")
    print("   □ Text is readable and well-sized")
    print("   □ Hover effects work on interactive elements")


def cleanup_processes(processes):
    """Clean up background processes."""
    print("\n🧹 Cleaning up processes...")
    for name, process in processes.items():
        if process:
            print(f"🛑 Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    print("✅ Cleanup complete")


def main():
    """Main validation function."""
    print("🚀 MULETA COGNITIVA - WEB INTERFACE VALIDATION")
    print("=" * 60)
    
    # Validation phase
    validation_passed = True
    
    if not validate_html_structure():
        validation_passed = False
    
    if not validate_javascript_functions():
        validation_passed = False
    
    if not validate_css_classes():
        validation_passed = False
    
    if not validation_passed:
        print("\n❌ Validation failed. Please fix the issues above.")
        return False
    
    print("\n✅ All static validations passed!")
    
    # Server startup phase
    processes = {}
    
    try:
        # Start API server
        api_process = start_api_server()
        processes['API'] = api_process
        
        if not api_process:
            print("❌ Cannot proceed without API server")
            return False
        
        # Start web server
        web_process = start_web_server()
        processes['Web'] = web_process
        
        if not web_process:
            print("❌ Cannot proceed without web server")
            cleanup_processes(processes)
            return False
        
        # Test API connectivity
        test_api_connectivity()
        
        # Open browser
        open_browser()
        
        # Print manual checklist
        print_manual_test_checklist()
        
        print(f"\n🎯 TESTING COMPLETE!")
        print(f"   • Web Interface: http://localhost:3000")
        print(f"   • API Server: http://localhost:8000")
        print(f"   • API Docs: http://localhost:8000/docs")
        
        print(f"\n⏱️  Press Ctrl+C to stop servers and exit")
        
        # Keep servers running until user interrupts
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n👋 Validation complete!")
            
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        return False
    
    finally:
        cleanup_processes(processes)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Validation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
