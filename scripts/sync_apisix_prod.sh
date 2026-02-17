#!/bin/bash
#
# Sync APISIX routes and upstreams from local to production
# Run this on the production server: ssh polmo "bash ~/sync_apisix_prod.sh"
#

set -e

echo "=== Syncing APISIX Configuration to Production ==="

# ==========================================
# UPSTREAMS
# ==========================================

echo "Creating/Updating OpenAI upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/openai-upstream '{
  "id": "openai-upstream",
  "create_time": 1770791421,
  "update_time": 1770791421,
  "nodes": {"api.openai.com:443": 1},
  "timeout": {"connect": 30, "send": 30, "read": 300},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "OpenAI API",
  "desc": "OpenAI API endpoint",
  "keepalive_pool": {"idle_timeout": 60, "requests": 1000, "size": 320}
}'

echo "Creating/Updating Anthropic upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/anthropic-upstream '{
  "id": "anthropic-upstream",
  "create_time": 1770791421,
  "update_time": 1770791421,
  "nodes": {"api.anthropic.com:443": 1},
  "timeout": {"connect": 30, "send": 120, "read": 300},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "rewrite",
  "upstream_host": "api.anthropic.com",
  "name": "Anthropic API",
  "retries": 2
}'

echo "Creating/Updating EXA upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/exa-upstream '{
  "id": "exa-upstream",
  "create_time": 1770791421,
  "update_time": 1770791421,
  "nodes": {"api.exa.ai:443": 1},
  "timeout": {"connect": 10, "send": 30, "read": 60},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "EXA AI API"
}'

echo "Creating/Updating DPA upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/dpa-upstream '{
  "id": "dpa-upstream",
  "create_time": 1770791421,
  "update_time": 1770791421,
  "nodes": {"article-retriever.iq.dpa-ai-hub.de:443": 1},
  "timeout": {"connect": 10, "send": 30, "read": 180},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "DPA News API"
}'

echo "Creating/Updating Bundestag upstream..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/upstreams/bundestag-upstream '{
  "id": "bundestag-upstream",
  "create_time": 1770791421,
  "update_time": 1770791421,
  "nodes": {"search.dip.bundestag.de:443": 1},
  "timeout": {"connect": 10, "send": 30, "read": 60},
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "node",
  "name": "Bundestag DIP API"
}'

# ==========================================
# OPENAI ROUTES
# ==========================================

echo "Creating OpenAI Chat Completions route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/openai-chat '{
  "id": "openai-chat",
  "uri": "/v1/chat/completions",
  "name": "OpenAI Chat Completions",
  "methods": ["POST"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "host": "api.openai.com",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "llm-cost-tracker": {
      "enabled": true,
      "log_debug": true
    },
    "limit-req": {
      "rate": 100,
      "burst": 50,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": ["return function(conf, ctx) local core = require(\"apisix.core\") local user_agent = core.request.header(ctx, \"User-Agent\") or \"\" if string.find(user_agent, \"OpenAI\") or string.find(user_agent, \"python\") then local agent_type = core.request.header(ctx, \"X-Agent-Type\") if not agent_type then core.request.set_header(ctx, \"X-Agent-Type\", \"kodosumi_flow\") core.request.set_header(ctx, \"X-Agent-Name\", \"graphiti_document_processor\") core.request.set_header(ctx, \"X-Flow-Name\", \"data_ingestion\") core.request.set_header(ctx, \"X-Project-ID\", \"political_monitoring_v2\") end end end"]
    }
  },
  "upstream_id": "openai-upstream"
}'

echo "Creating OpenAI Embeddings route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/openai-embeddings '{
  "id": "openai-embeddings",
  "uri": "/v1/embeddings",
  "name": "OpenAI Embeddings",
  "methods": ["POST"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "host": "api.openai.com",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "llm-cost-tracker": {
      "enabled": true,
      "log_debug": true
    },
    "limit-req": {
      "rate": 100,
      "burst": 50,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": ["return function(conf, ctx) local core = require(\"apisix.core\") local user_agent = core.request.header(ctx, \"User-Agent\") or \"\" if string.find(user_agent, \"OpenAI\") or string.find(user_agent, \"python\") then local agent_type = core.request.header(ctx, \"X-Agent-Type\") if not agent_type then core.request.set_header(ctx, \"X-Agent-Type\", \"kodosumi_flow\") core.request.set_header(ctx, \"X-Agent-Name\", \"graphiti_embedder\") core.request.set_header(ctx, \"X-Flow-Name\", \"data_ingestion\") core.request.set_header(ctx, \"X-Project-ID\", \"political_monitoring_v2\") end end end"]
    }
  },
  "upstream_id": "openai-upstream"
}'

echo "Creating OpenAI Models route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/openai-models '{
  "id": "openai-models",
  "uri": "/v1/models*",
  "name": "OpenAI Models",
  "methods": ["GET"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "host": "api.openai.com",
      "scheme": "https"
    }
  },
  "upstream_id": "openai-upstream"
}'

echo "Creating OpenAI Responses route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/openai-responses '{
  "id": "openai-responses",
  "uri": "/v1/responses*",
  "name": "OpenAI Responses API",
  "desc": "OpenAI Responses API (newer endpoint)",
  "methods": ["GET", "POST"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "host": "api.openai.com",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "llm-cost-tracker": {
      "enabled": true,
      "log_debug": true
    },
    "limit-req": {
      "rate": 100,
      "burst": 50,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": ["return function(conf, ctx) local core = require(\"apisix.core\") local user_agent = core.request.header(ctx, \"User-Agent\") or \"\" if string.find(user_agent, \"OpenAI\") or string.find(user_agent, \"python\") then local agent_type = core.request.header(ctx, \"X-Agent-Type\") if not agent_type then core.request.set_header(ctx, \"X-Agent-Type\", \"kodosumi_flow\") core.request.set_header(ctx, \"X-Agent-Name\", \"graphiti_document_processor\") core.request.set_header(ctx, \"X-Flow-Name\", \"data_ingestion\") core.request.set_header(ctx, \"X-Project-ID\", \"political_monitoring_v2\") end end end"]
    }
  },
  "upstream_id": "openai-upstream"
}'

# ==========================================
# ANTHROPIC ROUTES
# ==========================================

echo "Creating Anthropic Messages route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/anthropic-all '{
  "id": "anthropic-all",
  "uri": "/v1/messages*",
  "name": "Anthropic API (All Endpoints)",
  "methods": ["GET", "POST"],
  "priority": 10,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "host": "api.anthropic.com",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "llm-cost-tracker": {
      "enabled": true,
      "log_debug": true
    },
    "limit-req": {
      "rate": 50,
      "burst": 25,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "api-breaker": {
      "break_response_code": 503,
      "max_breaker_sec": 300,
      "unhealthy": {"http_statuses": [500, 502, 503, 504], "failures": 3},
      "healthy": {"http_statuses": [200, 201], "successes": 2}
    },
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": ["return function(conf, ctx) local core = require(\"apisix.core\") local user_agent = core.request.header(ctx, \"User-Agent\") or \"\" if string.find(user_agent, \"Anthropic\") or string.find(user_agent, \"python\") then local agent_type = core.request.header(ctx, \"X-Agent-Type\") if not agent_type then core.request.set_header(ctx, \"X-Agent-Type\", \"kodosumi_flow\") core.request.set_header(ctx, \"X-Agent-Name\", \"anthropic_agent\") core.request.set_header(ctx, \"X-Flow-Name\", \"data_ingestion\") core.request.set_header(ctx, \"X-Project-ID\", \"political_monitoring_v2\") end end end"]
    }
  },
  "upstream_id": "anthropic-upstream"
}'

echo "Creating Anthropic v1/v1 rewrite route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/anthropic-v1v1 '{
  "id": "anthropic-v1v1",
  "uri": "/v1/v1/messages*",
  "name": "Anthropic API (v1/v1 rewrite)",
  "desc": "Handles requests where base_url includes /v1 (e.g., from APISIX_GATEWAY_URL=http://localhost:9080/v1)",
  "methods": ["GET", "POST"],
  "priority": 15,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "host": "api.anthropic.com",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""},
      "regex_uri": ["^/v1(/v1/messages.*)$", "$1"]
    },
    "llm-cost-tracker": {
      "enabled": true,
      "log_debug": true
    },
    "limit-req": {
      "rate": 50,
      "burst": 25,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    },
    "api-breaker": {
      "break_response_code": 503,
      "max_breaker_sec": 300,
      "unhealthy": {"http_statuses": [500, 502, 503, 504], "failures": 3},
      "healthy": {"http_statuses": [200, 201], "successes": 2}
    },
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": ["return function(conf, ctx) local core = require(\"apisix.core\") local user_agent = core.request.header(ctx, \"User-Agent\") or \"\" if string.find(user_agent, \"Anthropic\") or string.find(user_agent, \"python\") then local agent_type = core.request.header(ctx, \"X-Agent-Type\") if not agent_type then core.request.set_header(ctx, \"X-Agent-Type\", \"kodosumi_flow\") core.request.set_header(ctx, \"X-Agent-Name\", \"anthropic_agent\") core.request.set_header(ctx, \"X-Flow-Name\", \"data_ingestion\") core.request.set_header(ctx, \"X-Project-ID\", \"political_monitoring_v2\") end end end"]
    }
  },
  "upstream_id": "anthropic-upstream"
}'

# ==========================================
# EXA AI ROUTES
# ==========================================

echo "Creating EXA Search route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/exa-search '{
  "id": "exa-search",
  "uri": "/exa/search",
  "name": "Exa Search API",
  "methods": ["POST"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "uri": "/search",
      "host": "api.exa.ai",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 10,
      "burst": 5,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "exa-upstream"
}'

echo "Creating EXA Contents route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/exa-contents '{
  "id": "exa-contents",
  "uri": "/exa/contents",
  "name": "Exa Contents API",
  "methods": ["POST"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "uri": "/contents",
      "host": "api.exa.ai",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 10,
      "burst": 5,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "exa-upstream"
}'

# ==========================================
# DPA NEWS ROUTES
# ==========================================

echo "Creating DPA Articles route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/dpa-articles '{
  "id": "dpa-articles",
  "uri": "/dpa/articles/*",
  "name": "DPA Articles API",
  "methods": ["POST"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/dpa(/articles/.*)$", "$1"],
      "host": "article-retriever.iq.dpa-ai-hub.de",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 5,
      "burst": 2,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "dpa-upstream"
}'

# ==========================================
# BUNDESTAG DIP ROUTES
# ==========================================

echo "Creating Bundestag Vorgang route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/bundestag-vorgang '{
  "id": "bundestag-vorgang",
  "uri": "/bundestag/vorgang*",
  "name": "Bundestag Vorgang API",
  "methods": ["GET"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/bundestag(/vorgang.*)$", "/api/v1$1"],
      "host": "search.dip.bundestag.de",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "bundestag-upstream"
}'

echo "Creating Bundestag Drucksache route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/bundestag-drucksache '{
  "id": "bundestag-drucksache",
  "uri": "/bundestag/drucksache*",
  "name": "Bundestag Drucksache API",
  "methods": ["GET"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/bundestag(/drucksache.*)$", "/api/v1$1"],
      "host": "search.dip.bundestag.de",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "bundestag-upstream"
}'

echo "Creating Bundestag Aktivitaet route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/bundestag-aktivitaet '{
  "id": "bundestag-aktivitaet",
  "uri": "/bundestag/aktivitaet*",
  "name": "Bundestag Aktivitaet API",
  "methods": ["GET"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/bundestag(/aktivitaet.*)$", "/api/v1$1"],
      "host": "search.dip.bundestag.de",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "bundestag-upstream"
}'

echo "Creating Bundestag Person route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/bundestag-person '{
  "id": "bundestag-person",
  "uri": "/bundestag/person*",
  "name": "Bundestag Person API",
  "methods": ["GET"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/bundestag(/person.*)$", "/api/v1$1"],
      "host": "search.dip.bundestag.de",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "bundestag-upstream"
}'

echo "Creating Bundestag Plenarprotokoll route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/bundestag-plenarprotokoll '{
  "id": "bundestag-plenarprotokoll",
  "uri": "/bundestag/plenarprotokoll*",
  "name": "Bundestag Plenarprotokoll API",
  "methods": ["GET"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/bundestag(/plenarprotokoll.*)$", "/api/v1$1"],
      "host": "search.dip.bundestag.de",
      "scheme": "https",
      "headers": {"Accept-Encoding": ""}
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "upstream_id": "bundestag-upstream"
}'

# ==========================================
# SYSTEM ROUTES
# ==========================================

echo "Creating APISIX Status route..."
sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/apisix-status '{
  "id": "apisix-status",
  "uri": "/apisix/status",
  "name": "APISIX Status Check",
  "methods": ["GET"],
  "priority": 0,
  "status": 1,
  "plugins": {
    "public-api": {}
  }
}'

# ==========================================
# CLEANUP OLD ROUTES
# ==========================================

echo ""
echo "Cleaning up old numbered routes..."
# Delete old timestamp-based route/upstream IDs
sudo docker exec policiytracker-etcd etcdctl del --prefix /apisix/routes/5969961998177097362
sudo docker exec policiytracker-etcd etcdctl del --prefix /apisix/upstreams/5969598388177097362
sudo docker exec policiytracker-etcd etcdctl del /apisix/upstreams/596959838819320524 2>/dev/null || true

echo ""
echo "=== Sync Complete ==="
echo ""
echo "Upstreams:"
sudo docker exec policiytracker-etcd etcdctl get /apisix/upstreams --prefix --keys-only
echo ""
echo "Routes:"
sudo docker exec policiytracker-etcd etcdctl get /apisix/routes --prefix --keys-only
