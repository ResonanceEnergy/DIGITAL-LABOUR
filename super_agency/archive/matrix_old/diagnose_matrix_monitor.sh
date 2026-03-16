#!/bin/bash
# Matrix Monitor Diagnostic Script
# Tests if the Matrix Monitor is updating and displaying properly

echo "🔍 Matrix Monitor Diagnostic Tool"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test 1: Check if services are running
echo -e "${BLUE}Test 1: Service Status${NC}"
echo "Checking if Matrix Monitor services are running..."

if pgrep -f "matrix_maximizer.py" > /dev/null; then
    echo -e "${GREEN}✅ Matrix Maximizer: RUNNING${NC}"
else
    echo -e "${RED}❌ Matrix Maximizer: NOT RUNNING${NC}"
fi

if pgrep -f "mobile_command_center_simple.py" > /dev/null; then
    echo -e "${GREEN}✅ Mobile Command Center: RUNNING${NC}"
else
    echo -e "${RED}❌ Mobile Command Center: NOT RUNNING${NC}"
fi

if pgrep -f "operations_api.py" > /dev/null; then
    echo -e "${GREEN}✅ Operations API: RUNNING${NC}"
else
    echo -e "${RED}❌ Operations API: NOT RUNNING${NC}"
fi

echo ""

# Test 2: Check API endpoints
echo -e "${BLUE}Test 2: API Endpoints${NC}"

# Test Matrix API
echo "Testing /api/matrix endpoint..."
if curl -s --max-time 5 http://localhost:3000/api/matrix > /dev/null 2>&1; then
    health=$(curl -s http://localhost:3000/api/matrix | jq -r '.system_health // "N/A"')
    nodes=$(curl -s http://localhost:3000/api/matrix | jq -r '.online_nodes // "N/A"')
    echo -e "${GREEN}✅ Matrix API: RESPONDING${NC} (Health: ${health}%, Nodes: ${nodes})"
else
    echo -e "${RED}❌ Matrix API: NOT RESPONDING${NC}"
fi

# Test System API
echo "Testing /api/system endpoint..."
if curl -s --max-time 5 http://localhost:3000/api/system > /dev/null 2>&1; then
    echo -e "${GREEN}✅ System API: RESPONDING${NC}"
else
    echo -e "${RED}❌ System API: NOT RESPONDING${NC}"
fi

# Test Agents API
echo "Testing /api/agents endpoint..."
if curl -s --max-time 5 http://localhost:3000/api/agents > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Agents API: RESPONDING${NC}"
else
    echo -e "${RED}❌ Agents API: NOT RESPONDING${NC}"
fi

# Test Alerts API
echo "Testing /api/alerts endpoint..."
if curl -s --max-time 5 http://localhost:3000/api/alerts > /dev/null 2>&1; then
    alert_count=$(curl -s http://localhost:3000/api/alerts | jq -r 'length')
    echo -e "${GREEN}✅ Alerts API: RESPONDING${NC} (${alert_count} alerts)"
else
    echo -e "${RED}❌ Alerts API: NOT RESPONDING${NC}"
fi

echo ""

# Test 3: Check web interface
echo -e "${BLUE}Test 3: Web Interface${NC}"

# Test main page
echo "Testing main web interface..."
if curl -s --max-time 5 -I http://localhost:3000/ | grep -q "200 OK"; then
    echo -e "${GREEN}✅ Main Page: ACCESSIBLE${NC}"
else
    echo -e "${RED}❌ Main Page: NOT ACCESSIBLE${NC}"
fi

# Test static files
echo "Testing JavaScript file..."
if curl -s --max-time 5 -I http://localhost:3000/static/js/matrix_maximizer.js | grep -q "200 OK"; then
    echo -e "${GREEN}✅ JavaScript: ACCESSIBLE${NC}"
else
    echo -e "${RED}❌ JavaScript: NOT ACCESSIBLE${NC}"
fi

echo "Testing CSS file..."
if curl -s --max-time 5 -I http://localhost:3000/static/css/matrix_maximizer.css | grep -q "200 OK"; then
    echo -e "${GREEN}✅ CSS: ACCESSIBLE${NC}"
else
    echo -e "${RED}❌ CSS: NOT ACCESSIBLE${NC}"
fi

echo ""

# Test 4: Data freshness check
echo -e "${BLUE}Test 4: Data Freshness${NC}"

timestamp=$(curl -s http://localhost:3000/api/matrix | jq -r '.timestamp // "N/A"')
if [ "$timestamp" != "N/A" ]; then
    # Convert timestamp to seconds since epoch
    api_time=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${timestamp%%.*}" +%s 2>/dev/null || echo "0")
    current_time=$(date +%s)
    time_diff=$((current_time - api_time))

    if [ $time_diff -lt 300 ]; then  # Less than 5 minutes old
        echo -e "${GREEN}✅ Data Freshness: CURRENT${NC} (${time_diff}s ago)"
    elif [ $time_diff -lt 3600 ]; then  # Less than 1 hour old
        echo -e "${YELLOW}⚠️  Data Freshness: STALE${NC} (${time_diff}s ago)"
    else
        echo -e "${RED}❌ Data Freshness: VERY STALE${NC} (${time_diff}s ago)"
    fi
else
    echo -e "${RED}❌ Data Freshness: UNKNOWN${NC}"
fi

echo ""

# Test 5: Mobile Command Center
echo -e "${BLUE}Test 5: Mobile Command Center${NC}"

# Test mobile API
echo "Testing mobile /api/matrix endpoint..."
if curl -s --max-time 5 http://localhost:8081/api/matrix > /dev/null 2>&1; then
    mobile_health=$(curl -s http://localhost:8081/api/matrix | jq -r '.system_health // "N/A"')
    echo -e "${GREEN}✅ Mobile API: RESPONDING${NC} (Health: ${mobile_health}%)"
else
    echo -e "${RED}❌ Mobile API: NOT RESPONDING${NC}"
fi

# Test mobile web interface
echo "Testing mobile web interface..."
if curl -s --max-time 5 -I http://localhost:8081/ | grep -q "200 OK"; then
    echo -e "${GREEN}✅ Mobile Web: ACCESSIBLE${NC}"
else
    echo -e "${RED}❌ Mobile Web: NOT ACCESSIBLE${NC}"
fi

echo ""

# Summary and recommendations
echo -e "${BLUE}📋 Summary & Recommendations${NC}"
echo "================================"

# Count failures
failures=0
if ! pgrep -f "matrix_maximizer.py" > /dev/null; then ((failures++)); fi
if ! curl -s --max-time 5 http://localhost:3000/api/matrix > /dev/null 2>&1; then ((failures++)); fi
if ! curl -s --max-time 5 -I http://localhost:3000/ | grep -q "200 OK"; then ((failures++)); fi

if [ $failures -eq 0 ]; then
    echo -e "${GREEN}✅ All systems operational!${NC}"
    echo ""
    echo "If the Matrix Monitor still isn't updating in your browser:"
    echo "1. Hard refresh the page (Ctrl+F5 or Cmd+Shift+R)"
    echo "2. Clear browser cache"
    echo "3. Check browser developer tools for JavaScript errors"
    echo "4. Ensure JavaScript is enabled"
else
    echo -e "${RED}❌ Issues detected. Try these fixes:${NC}"
    echo ""
    if ! pgrep -f "matrix_maximizer.py" > /dev/null; then
        echo "• Start Matrix Maximizer: python3 matrix_maximizer.py"
    fi
    if ! curl -s --max-time 5 http://localhost:3000/api/matrix > /dev/null 2>&1; then
        echo "• Check for port conflicts on 3000"
        echo "• Restart the matrix maximizer service"
    fi
    if ! curl -s --max-time 5 -I http://localhost:3000/ | grep -q "200 OK"; then
        echo "• Check if the web server is running on port 3000"
    fi
fi

echo ""
echo -e "${YELLOW}🔗 Access URLs:${NC}"
echo "Matrix Monitor: http://localhost:3000"
echo "Mobile Command Center: http://localhost:8081"
echo "iPhone Dashboard: http://localhost:8081/iphone"
echo "iPad Dashboard: http://localhost:8081/ipad"
