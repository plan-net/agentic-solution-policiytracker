#!/bin/bash
# Script to update APISIX route to inject Graphiti agent headers

APISIX_ADMIN_URL="http://localhost:9180/apisix/admin"
API_KEY="edd1c9f034335f136f87ad84b625c8f1"

# Get the current openai-route configuration
ROUTE_ID=$(curl -s "${APISIX_ADMIN_URL}/routes" -H "X-API-KEY: ${API_KEY}" | \
  python3 -c "import sys, json; routes = json.load(sys.stdin); print([r['value']['id'] for r in routes.get('list', []) if r['value'].get('name') == 'openai-route'][0] if routes.get('list') else '')")

if [ -z "$ROUTE_ID" ]; then
  echo "❌ Could not find openai-route"
  exit 1
fi

echo "✓ Found route ID: $ROUTE_ID"

# Update the route with serverless-pre-function plugin
curl -i "${APISIX_ADMIN_URL}/routes/${ROUTE_ID}" \
  -H "X-API-KEY: ${API_KEY}" \
  -X PATCH \
  -d '{
    "plugins": {
      "serverless-pre-function": {
        "phase": "rewrite",
        "functions": [
          "return function(conf, ctx) local core = require(\"apisix.core\") local user_agent = core.request.header(ctx, \"User-Agent\") or \"\" if string.find(user_agent, \"AsyncOpenAI\") then local agent_type = core.request.header(ctx, \"X-Agent-Type\") if not agent_type then core.request.set_header(ctx, \"X-Agent-Type\", \"kodosumi_flow\") core.request.set_header(ctx, \"X-Agent-Name\", \"graphiti_document_processor\") core.request.set_header(ctx, \"X-Flow-Name\", \"data_ingestion\") core.request.set_header(ctx, \"X-Project-ID\", \"political_monitoring_v2\") core.log.info(\"Injected default Graphiti agent headers for User-Agent: \", user_agent) end end end"
        ]
      }
    }
  }'

echo ""
echo "✅ Route updated with serverless-pre-function plugin"
echo "🔄 The plugin will now inject agent headers for Graphiti calls (User-Agent: AsyncOpenAI)"
