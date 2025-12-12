#!/bin/bash
# Quick API Validation Script
# 运行此脚本快速验证所有 Iter2 功能

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Iter2 API 功能验证${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 1: 201 Created
echo -e "${BLUE}[Test 1] POST /users - 201 Created${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test'$RANDOM'@example.com",
    "phone": "+1'$(shuf -i 1000000000-9999999999 -n 1)'",
    "membership_tier": "PRO",
    "password": "TestPassword123"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
USER_ID=$(echo "$BODY" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 | head -1)

if [ "$HTTP_CODE" = "201" ]; then
  echo -e "${GREEN}✅ Status 201 Created - PASS${NC}"
  echo "User ID: $USER_ID"
else
  echo -e "${RED}❌ Status $HTTP_CODE - FAIL${NC}"
fi
echo ""

# Test 2: ETag - 304 Not Modified
echo -e "${BLUE}[Test 2] GET /users/{id} with If-None-Match - 304 Not Modified${NC}"
RESPONSE=$(curl -s -i -X GET "$BASE_URL/users/$USER_ID")
ETAG=$(echo "$RESPONSE" | grep -i "etag:" | cut -d' ' -f2 | tr -d '\r')

if [ ! -z "$ETAG" ]; then
  echo "ETag: $ETAG"
  
  RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/users/$USER_ID" \
    -H "If-None-Match: $ETAG")
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  
  if [ "$HTTP_CODE" = "304" ]; then
    echo -e "${GREEN}✅ Status 304 Not Modified - PASS${NC}"
  else
    echo -e "${RED}❌ Status $HTTP_CODE - FAIL (expected 304)${NC}"
  fi
else
  echo -e "${RED}❌ No ETag found - FAIL${NC}"
fi
echo ""

# Test 3: 412 Precondition Failed
echo -e "${BLUE}[Test 3] PATCH /users/{id} with Wrong If-Match - 412 Precondition Failed${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/users/$USER_ID" \
  -H "Content-Type: application/json" \
  -H "If-Match: wrong-etag" \
  -d '{"name": "Updated Name"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "412" ]; then
  echo -e "${GREEN}✅ Status 412 Precondition Failed - PASS${NC}"
else
  echo -e "${RED}❌ Status $HTTP_CODE - FAIL (expected 412)${NC}"
fi
echo ""

# Test 4: Query Parameters
echo -e "${BLUE}[Test 4] GET /users?name=... - Query Filtering${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/users?name=Test%20User")
COUNT=$(echo "$RESPONSE" | grep -o '"id"' | wc -l)

if [ "$COUNT" -gt 0 ]; then
  echo -e "${GREEN}✅ Query filtering works - PASS (found $COUNT records)${NC}"
else
  echo -e "${RED}❌ Query filtering failed - FAIL${NC}"
fi
echo ""

# Test 5: HATEOAS Links
echo -e "${BLUE}[Test 5] GET /users/{id} - HATEOAS _links${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/users/$USER_ID")
HAS_LINKS=$(echo "$RESPONSE" | grep -o '"_links"' | wc -l)

if [ "$HAS_LINKS" -gt 0 ]; then
  echo -e "${GREEN}✅ HATEOAS _links present - PASS${NC}"
  echo "$RESPONSE" | grep -o '"_links".*' | head -c 100
  echo ""
else
  echo -e "${RED}❌ HATEOAS _links missing - FAIL${NC}"
fi
echo ""

# Test 6: 201 Created Profile
echo -e "${BLUE}[Test 6] POST /profiles - 201 Created${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "username": "testuser'$RANDOM'",
    "display_name": "Test Display",
    "bio": "Test bio"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
PROFILE_ID=$(echo "$RESPONSE" | sed '$d' | grep -o '"id":"[^"]*"' | cut -d'"' -f4 | head -1)

if [ "$HTTP_CODE" = "201" ]; then
  echo -e "${GREEN}✅ Status 201 Created - PASS${NC}"
  echo "Profile ID: $PROFILE_ID"
else
  echo -e "${RED}❌ Status $HTTP_CODE - FAIL${NC}"
fi
echo ""

# Test 7: 1:1 Constraint
echo -e "${BLUE}[Test 7] POST /profiles (Duplicate) - 1:1 Constraint${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "username": "testuser'$RANDOM'2",
    "display_name": "Another Profile"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "400" ]; then
  echo -e "${GREEN}✅ Status 400 Bad Request (1:1 constraint) - PASS${NC}"
else
  echo -e "${RED}❌ Status $HTTP_CODE - FAIL (expected 400)${NC}"
fi
echo ""

# Test 8: 404 Not Found
echo -e "${BLUE}[Test 8] GET /users/{non-existent} - 404 Not Found${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/users/00000000-0000-0000-0000-000000000000")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "404" ]; then
  echo -e "${GREEN}✅ Status 404 Not Found - PASS${NC}"
else
  echo -e "${RED}❌ Status $HTTP_CODE - FAIL (expected 404)${NC}"
fi
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}验证完成!${NC}"
echo -e "${BLUE}========================================${NC}"

