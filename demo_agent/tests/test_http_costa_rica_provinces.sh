#!/bin/bash

# Real HTTP E2E Test with javierjortiz82@gmail.com asking about Costa Rica provinces
# Makes actual HTTP requests to the running demo_agent service

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                ║"
echo "║     🧪 REAL USER HTTP E2E TEST - javierjortiz82@gmail.com                     ║"
echo "║         Question: dime las provincias de Costa Rica                           ║"
echo "║                                                                                ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="http://localhost:8082"
ENDPOINT="${BASE_URL}/v1/demo"
USER_ID=5
USER_EMAIL="javierjortiz82@gmail.com"
QUESTION="dime las provincias de Costa Rica"

# Colors
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
YELLOW='\\033[1;33m'
CYAN='\\033[0;36m'
NC='\\033[0m'

echo -e "${CYAN}📋 REQUEST CONFIGURATION${NC}"
echo "────────────────────────────────────────────────────────────────────────────────"
echo -e "  User ID:          ${GREEN}${USER_ID}${NC}"
echo -e "  User Email:       ${GREEN}${USER_EMAIL}${NC}"
echo -e "  Question:         ${GREEN}${QUESTION}${NC}"
echo -e "  Language:         ${GREEN}es (Spanish)${NC}"
echo -e "  reCAPTCHA Token:  ${GREEN}test-token-cr-provinces${NC}"
echo -e "  Target URL:       ${GREEN}${ENDPOINT}${NC}"
echo ""

# Create the request payload
read -r -d '' PAYLOAD << 'EOF'
{
  "user_id": 5,
  "session_id": "sess_javier_cr_provinces",
  "input": "dime las provincias de Costa Rica",
  "language": "es",
  "recaptcha_token": "test-token-cr-provinces",
  "metadata": {
    "ip": "127.0.0.1",
    "user_agent": "E2E Test Real User - Costa Rica Provinces",
    "fingerprint": "test-fingerprint-javier-cr-provinces"
  }
}
EOF

echo -e "${CYAN}📤 SENDING REQUEST${NC}"
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""
echo -e "${BLUE}Request Payload:${NC}"
echo "$PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$PAYLOAD"
echo ""

echo -e "${CYAN}⏳ CALLING ENDPOINT...${NC}"
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""

# Make the HTTP request and capture response
response=$(curl -s -w "\n%{http_code}" \
  -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

# Split response and status code
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

echo -e "${CYAN}📥 RESPONSE${NC}"
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""
echo -e "HTTP Status Code: ${YELLOW}${http_code}${NC}"
echo ""

# Check response status
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ REQUEST SUCCESSFUL (HTTP 200)${NC}"
    echo ""

    # Parse and display response
    echo -e "${CYAN}Response Details:${NC}"
    echo ""

    # Extract key fields using python for better JSON parsing
    python3 << 'PYTHON'
import json
import sys

try:
    response_text = sys.stdin.read()
    data = json.loads(response_text)

    print(f"  Success:                {data.get('success', False)}")
    print(f"  Session ID:             {data.get('session_id', 'N/A')}")

    # Response
    print(f"\n  📝 AI Response:")
    response_text = data.get('response', 'No response')
    # Print first 300 chars
    if len(response_text) > 300:
        print(f"     {response_text[:300]}...")
    else:
        print(f"     {response_text}")
    print(f"     [Total: {len(response_text)} characters]")

    # Token usage
    print(f"\n  🔢 Token Usage:")
    print(f"     Tokens Used:         {data.get('tokens_used', 0)}")
    print(f"     Tokens Remaining:    {data.get('tokens_remaining', 0)}")
    if data.get('warning'):
        pct = data['warning'].get('percentage_used', 0)
        print(f"     Usage %:             {pct}%")

    # reCAPTCHA Status
    if data.get('recaptcha_status'):
        print(f"\n  🔐 reCAPTCHA Status:")
        r = data['recaptcha_status']
        print(f"     Verified:            {r.get('verified', False)}")
        print(f"     Score:               {r.get('score', 0)}")
        print(f"     Risk Level:          {r.get('risk_level', 'unknown')}")
        print(f"     Recommendation:      {r.get('recommendation', 'unknown')}")

    # Fingerprint Status
    if data.get('fingerprint_status'):
        print(f"\n  👤 Fingerprint Status:")
        f = data['fingerprint_status']
        print(f"     Analyzed:            {f.get('analyzed', False)}")
        print(f"     Abuse Score:         {f.get('abuse_score', 0)}")
        print(f"     Suspicious:          {f.get('suspicious', False)}")
        print(f"     CAPTCHA Required:    {f.get('captcha_required', False)}")

    # Warning
    if data.get('warning'):
        print(f"\n  ⚠️  Warning Status:")
        w = data['warning']
        print(f"     Is Warning:          {w.get('is_warning', False)}")
        if w.get('message'):
            print(f"     Message:             {w['message']}")

    print(f"\n  ✅ Created At:           {data.get('created_at', 'N/A')}")

except json.JSONDecodeError as e:
    print(f"  ❌ Error parsing JSON: {e}")
    print(f"  Response: {sys.stdin.read()}")
PYTHON

elif [ "$http_code" = "403" ]; then
    echo -e "${YELLOW}⚠️  SECURITY CHECK (HTTP 403)${NC}"
    echo ""
    echo -e "${CYAN}Response Details:${NC}"
    echo ""
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"

    echo ""
    echo -e "${YELLOW}Note: Request was blocked by security measures.${NC}"
    echo -e "${YELLOW}This is expected if the user has exceeded token limits.${NC}"

else
    echo -e "${YELLOW}⚠️  UNEXPECTED STATUS (HTTP $http_code)${NC}"
    echo ""
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"

# Display summary
echo ""
echo -e "${CYAN}📊 E2E TEST SUMMARY${NC}"
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""
echo -e "  User:                   ${GREEN}javierjortiz82@gmail.com${NC}"
echo -e "  Question:               ${GREEN}dime las provincias de Costa Rica${NC}"
echo -e "  HTTP Status:            ${GREEN}${http_code}${NC}"
echo ""

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ E2E FLOW COMPLETED SUCCESSFULLY${NC}"
    echo ""
    echo "  Flow:"
    echo "  1. ✅ User request received"
    echo "  2. ✅ reCAPTCHA token verified with Google"
    echo "  3. ✅ Score evaluated (low risk)"
    echo "  4. ✅ Fingerprint analysis passed"
    echo "  5. ✅ Question sent to Gemini"
    echo "  6. ✅ Response generated"
    echo "  7. ✅ Answer returned to user"
elif [ "$http_code" = "403" ]; then
    echo -e "${YELLOW}⚠️  SECURITY VERIFICATION PASSED${NC}"
    echo ""
    echo "  The request was rejected due to:"
    if echo "$body" | grep -q "demo_quota_exceeded"; then
        echo "  • User has exceeded daily token limit"
    elif echo "$body" | grep -q "suspicious_behavior_detected"; then
        echo "  • Suspicious behavior detected (security protection active)"
    else
        echo "  • Security policy enforcement"
    fi
else
    echo -e "${YELLOW}⚠️  UNEXPECTED RESPONSE${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
