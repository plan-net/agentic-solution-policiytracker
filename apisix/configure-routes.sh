#!/bin/bash
# Script to configure APISIX routes via etcd

set -e

echo "Configuring APISIX routes via etcd..."

# Create OpenAI upstream
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/upstreams/openai-upstream '{
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "pass",
  "nodes": {
    "api.openai.com:443": 1
  },
  "timeout": {
    "connect": 30,
    "send": 120,
    "read": 300
  },
  "retries": 2
}'

echo "✓ Created OpenAI upstream"

# Create Anthropic upstream
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/upstreams/anthropic-upstream '{
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "pass",
  "nodes": {
    "api.anthropic.com:443": 1
  },
  "timeout": {
    "connect": 30,
    "send": 120,
    "read": 300
  },
  "retries": 2
}'

echo "✓ Created Anthropic upstream"

# Create OpenAI chat completions route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/openai-chat '{
  "uri": "/v1/chat/completions",
  "name": "OpenAI Chat Completions",
  "methods": ["POST"],
  "upstream_id": "openai-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "api.openai.com"
    },
    "limit-req": {
      "rate": 100,
      "burst": 50,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created OpenAI chat completions route"

# Create Anthropic messages route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/anthropic-messages '{
  "uri": "/v1/messages",
  "name": "Anthropic Messages",
  "methods": ["POST"],
  "upstream_id": "anthropic-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "api.anthropic.com"
    },
    "limit-req": {
      "rate": 50,
      "burst": 25,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Anthropic messages route"

echo ""
echo "✅ All routes configured successfully!"
echo ""
echo "You can now use APISIX as a gateway:"
echo "  OpenAI:    http://localhost:9080/v1/chat/completions"
echo "  Anthropic: http://localhost:9080/v1/messages"
echo "  Status:    http://localhost:9080/apisix/status"
