#!/bin/bash
#
# Setup APISIX routes and upstreams for Policy Tracker
# Run this on the production server: ssh polmo "bash ~/setup_apisix_routes.sh"
#

set -e

# Generate unique IDs for new routes/upstreams (timestamp-based)
TIMESTAMP=$(date +%s)
ANTHROPIC_UPSTREAM_ID="5969598388${TIMESTAMP}01"
EXA_UPSTREAM_ID="5969598388${TIMESTAMP}02"
DPA_UPSTREAM_ID="5969598388${TIMESTAMP}03"
BUNDESTAG_UPSTREAM_ID="5969598388${TIMESTAMP}04"

ANTHROPIC_ROUTE_ID="5969961998${TIMESTAMP}01"
EXA_SEARCH_ROUTE_ID="5969961998${TIMESTAMP}02"
EXA_CONTENTS_ROUTE_ID="5969961998${TIMESTAMP}03"
DPA_ROUTE_ID="5969961998${TIMESTAMP}04"
BUNDESTAG_VORGANG_ROUTE_ID="5969961998${TIMESTAMP}05"
BUNDESTAG_DRUCKSACHE_ROUTE_ID="5969961998${TIMESTAMP}06"

echo "=== Creating APISIX Upstreams and Routes ==="

# ==========================================
# ANTHROPIC UPSTREAM
# ==========================================
echo "Creating Anthropic upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/${ANTHROPIC_UPSTREAM_ID} '{
  "id": "'${ANTHROPIC_UPSTREAM_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "nodes": [{"host": "api.anthropic.com", "port": 443, "weight": 1}],
  "timeout": {"connect": 30, "send": 30, "read": 300},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "anthropic-upstream",
  "desc": "Anthropic Claude API endpoint"
}'

# ==========================================
# EXA AI UPSTREAM
# ==========================================
echo "Creating EXA AI upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/${EXA_UPSTREAM_ID} '{
  "id": "'${EXA_UPSTREAM_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "nodes": [{"host": "api.exa.ai", "port": 443, "weight": 1}],
  "timeout": {"connect": 10, "send": 30, "read": 60},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "exa-upstream",
  "desc": "EXA AI Web Search API"
}'

# ==========================================
# DPA NEWS UPSTREAM
# ==========================================
echo "Creating DPA News upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/${DPA_UPSTREAM_ID} '{
  "id": "'${DPA_UPSTREAM_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "nodes": [{"host": "article-retriever.iq.dpa-ai-hub.de", "port": 443, "weight": 1}],
  "timeout": {"connect": 10, "send": 30, "read": 180},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "dpa-upstream",
  "desc": "DPA News API (German Press Agency)"
}'

# ==========================================
# BUNDESTAG DIP UPSTREAM
# ==========================================
echo "Creating Bundestag DIP upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/${BUNDESTAG_UPSTREAM_ID} '{
  "id": "'${BUNDESTAG_UPSTREAM_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "nodes": [{"host": "search.dip.bundestag.de", "port": 443, "weight": 1}],
  "timeout": {"connect": 10, "send": 30, "read": 60},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "bundestag-upstream",
  "desc": "Bundestag DIP API (German Parliament)"
}'

# ==========================================
# ANTHROPIC ROUTE
# ==========================================
echo "Creating Anthropic route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/${ANTHROPIC_ROUTE_ID} '{
  "id": "'${ANTHROPIC_ROUTE_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "uri": "/v1/messages*",
  "name": "anthropic-messages",
  "desc": "Anthropic Claude Messages API with cost tracking",
  "methods": ["GET", "POST"],
  "priority": 10,
  "plugins": {
    "proxy-rewrite": {
      "headers": {"Accept-Encoding": ""},
      "host": "api.anthropic.com",
      "scheme": "https"
    },
    "llm-cost-tracker": {
      "enabled": true,
      "log_debug": true
    }
  },
  "upstream_id": "'${ANTHROPIC_UPSTREAM_ID}'",
  "status": 1
}'

# ==========================================
# EXA SEARCH ROUTE
# ==========================================
echo "Creating EXA Search route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/${EXA_SEARCH_ROUTE_ID} '{
  "id": "'${EXA_SEARCH_ROUTE_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "uri": "/exa/search",
  "name": "exa-search",
  "desc": "EXA AI Search API",
  "methods": ["POST"],
  "priority": 5,
  "plugins": {
    "proxy-rewrite": {
      "uri": "/search",
      "headers": {"Accept-Encoding": ""},
      "host": "api.exa.ai",
      "scheme": "https"
    },
    "limit-req": {
      "rate": 10,
      "burst": 5,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "api-request-tracker": {
      "enabled": true,
      "api_name": "exa-search",
      "analytics_host": "cost-analytics",
      "analytics_port": 8000,
      "log_debug": true
    }
  },
  "upstream_id": "'${EXA_UPSTREAM_ID}'",
  "status": 1
}'

# ==========================================
# EXA CONTENTS ROUTE
# ==========================================
echo "Creating EXA Contents route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/${EXA_CONTENTS_ROUTE_ID} '{
  "id": "'${EXA_CONTENTS_ROUTE_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "uri": "/exa/contents",
  "name": "exa-contents",
  "desc": "EXA AI Contents API",
  "methods": ["POST"],
  "priority": 5,
  "plugins": {
    "proxy-rewrite": {
      "uri": "/contents",
      "headers": {"Accept-Encoding": ""},
      "host": "api.exa.ai",
      "scheme": "https"
    },
    "limit-req": {
      "rate": 10,
      "burst": 5,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "api-request-tracker": {
      "enabled": true,
      "api_name": "exa-contents",
      "analytics_host": "cost-analytics",
      "analytics_port": 8000,
      "log_debug": true
    }
  },
  "upstream_id": "'${EXA_UPSTREAM_ID}'",
  "status": 1
}'

# ==========================================
# DPA ARTICLES ROUTE
# ==========================================
echo "Creating DPA Articles route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/${DPA_ROUTE_ID} '{
  "id": "'${DPA_ROUTE_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "uri": "/dpa/articles/relevant",
  "name": "dpa-articles",
  "desc": "DPA News Relevant Articles API",
  "methods": ["POST"],
  "priority": 5,
  "plugins": {
    "proxy-rewrite": {
      "uri": "/articles/relevant",
      "headers": {"Accept-Encoding": ""},
      "host": "article-retriever.iq.dpa-ai-hub.de",
      "scheme": "https"
    },
    "limit-req": {
      "rate": 5,
      "burst": 2,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "api-request-tracker": {
      "enabled": true,
      "api_name": "dpa-articles",
      "analytics_host": "cost-analytics",
      "analytics_port": 8000,
      "log_debug": true
    }
  },
  "upstream_id": "'${DPA_UPSTREAM_ID}'",
  "status": 1
}'

# ==========================================
# BUNDESTAG VORGANG ROUTE
# ==========================================
echo "Creating Bundestag Vorgang route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/${BUNDESTAG_VORGANG_ROUTE_ID} '{
  "id": "'${BUNDESTAG_VORGANG_ROUTE_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "uri": "/bundestag/vorgang*",
  "name": "bundestag-vorgang",
  "desc": "Bundestag DIP Vorgang (Legislative Procedures) API",
  "methods": ["GET"],
  "priority": 5,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/bundestag(/vorgang.*)$", "/api/v1$1"],
      "headers": {"Accept-Encoding": ""},
      "host": "search.dip.bundestag.de",
      "scheme": "https"
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "api-request-tracker": {
      "enabled": true,
      "api_name": "bundestag-vorgang",
      "analytics_host": "cost-analytics",
      "analytics_port": 8000,
      "log_debug": true
    }
  },
  "upstream_id": "'${BUNDESTAG_UPSTREAM_ID}'",
  "status": 1
}'

# ==========================================
# BUNDESTAG DRUCKSACHE ROUTE
# ==========================================
echo "Creating Bundestag Drucksache route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/${BUNDESTAG_DRUCKSACHE_ROUTE_ID} '{
  "id": "'${BUNDESTAG_DRUCKSACHE_ROUTE_ID}'",
  "create_time": '${TIMESTAMP}',
  "update_time": '${TIMESTAMP}',
  "uri": "/bundestag/drucksache*",
  "name": "bundestag-drucksache",
  "desc": "Bundestag DIP Drucksache (Parliamentary Documents) API",
  "methods": ["GET"],
  "priority": 5,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/bundestag(/drucksache.*)$", "/api/v1$1"],
      "headers": {"Accept-Encoding": ""},
      "host": "search.dip.bundestag.de",
      "scheme": "https"
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "api-request-tracker": {
      "enabled": true,
      "api_name": "bundestag-drucksache",
      "analytics_host": "cost-analytics",
      "analytics_port": 8000,
      "log_debug": true
    }
  },
  "upstream_id": "'${BUNDESTAG_UPSTREAM_ID}'",
  "status": 1
}'

echo ""
echo "=== Setup Complete ==="
echo "Created upstreams:"
echo "  - anthropic-upstream (${ANTHROPIC_UPSTREAM_ID})"
echo "  - exa-upstream (${EXA_UPSTREAM_ID})"
echo "  - dpa-upstream (${DPA_UPSTREAM_ID})"
echo "  - bundestag-upstream (${BUNDESTAG_UPSTREAM_ID})"
echo ""
echo "Created routes:"
echo "  - anthropic-messages (${ANTHROPIC_ROUTE_ID})"
echo "  - exa-search (${EXA_SEARCH_ROUTE_ID})"
echo "  - exa-contents (${EXA_CONTENTS_ROUTE_ID})"
echo "  - dpa-articles (${DPA_ROUTE_ID})"
echo "  - bundestag-vorgang (${BUNDESTAG_VORGANG_ROUTE_ID})"
echo "  - bundestag-drucksache (${BUNDESTAG_DRUCKSACHE_ROUTE_ID})"
echo ""
echo "Verify with: sudo docker exec policiytracker-etcd etcdctl get /apisix/routes --prefix --keys-only"
