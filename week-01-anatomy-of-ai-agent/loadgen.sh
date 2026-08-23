#!/bin/bash
TOKEN="${TOKEN:-<YOUR_COGNITO_BEARER_TOKEN>}"
GATEWAY_URL="${GATEWAY_URL:-https://<GATEWAY_ID>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/customer-support-ab/invocations}"

if [ "$TOKEN" = "<YOUR_COGNITO_BEARER_TOKEN>" ]; then
  echo "Error: Please set the TOKEN environment variable before running this script."
  echo "Usage: TOKEN=\"your_jwt_token\" [GATEWAY_URL=\"your_gateway_url\"] ./loadgen.sh"
  exit 1
fi

PROMPTS=(
  "What's the price of the Smart Watch?"
  "My headphones are broken, what should I do?"
  "Is PROD-002 still under warranty?"
  "What's the return policy for audio products?"
  "It stopped working. Can I get a refund?"
  "I want to return my USB-C Hub and check its warranty."
)

for i in $(seq 1 30); do
  PROMPT="${PROMPTS[$(( (i - 1) % ${#PROMPTS[@]} ))]}"
  SESSION_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()) + '-' + str(uuid.uuid4())[:8])")
  echo "=== Request $i: $PROMPT ==="
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: $SESSION_ID" \
    -d "{\"prompt\": \"$PROMPT\"}" \
    -X POST "$GATEWAY_URL"
  echo ""
  sleep 2
done
