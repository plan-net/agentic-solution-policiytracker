#!/bin/bash
# Script to configure external API routes in APISIX via etcd
# These routes enable tracking of non-LLM API usage (Exa, DPA, Bundestag)

set -e

echo "Configuring external API routes via etcd..."

# =============================================================================
# UPSTREAMS
# =============================================================================

# Create Exa.ai upstream
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/upstreams/exa-upstream '{
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "pass",
  "nodes": {
    "api.exa.ai:443": 1
  },
  "timeout": {
    "connect": 30,
    "send": 60,
    "read": 120
  },
  "retries": 2
}'

echo "✓ Created Exa.ai upstream"

# Create DPA upstream
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/upstreams/dpa-upstream '{
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "pass",
  "nodes": {
    "article-retriever.iq.dpa-ai-hub.de:443": 1
  },
  "timeout": {
    "connect": 30,
    "send": 60,
    "read": 120
  },
  "retries": 2
}'

echo "✓ Created DPA upstream"

# Create Bundestag DIP API upstream
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/upstreams/bundestag-upstream '{
  "type": "roundrobin",
  "scheme": "https",
  "pass_host": "pass",
  "nodes": {
    "search.dip.bundestag.de:443": 1
  },
  "timeout": {
    "connect": 30,
    "send": 60,
    "read": 120
  },
  "retries": 2
}'

echo "✓ Created Bundestag DIP upstream"

# =============================================================================
# ROUTES - Exa.ai
# =============================================================================

# Exa Search API route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/exa-search '{
  "uri": "/exa/search",
  "name": "Exa Search API",
  "methods": ["POST"],
  "upstream_id": "exa-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "api.exa.ai",
      "uri": "/search"
    },
    "api-request-tracker": {
      "api_name": "exa-search",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 30,
      "burst": 15,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Exa search route"

# Exa Contents API route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/exa-contents '{
  "uri": "/exa/contents",
  "name": "Exa Contents API",
  "methods": ["POST"],
  "upstream_id": "exa-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "api.exa.ai",
      "uri": "/contents"
    },
    "api-request-tracker": {
      "api_name": "exa-contents",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 30,
      "burst": 15,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Exa contents route"

# =============================================================================
# ROUTES - DPA
# =============================================================================

# DPA Articles API route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/dpa-articles '{
  "uri": "/dpa/articles/*",
  "name": "DPA Articles API",
  "methods": ["GET", "POST"],
  "upstream_id": "dpa-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "article-retriever.iq.dpa-ai-hub.de",
      "regex_uri": ["^/dpa/articles/(.*)$", "/articles/$1"]
    },
    "api-request-tracker": {
      "api_name": "dpa-articles",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 20,
      "burst": 10,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created DPA articles route"

# =============================================================================
# ROUTES - Bundestag DIP API
# =============================================================================

# Bundestag Vorgang (Legislative Procedures) route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/bundestag-vorgang '{
  "uri": "/bundestag/vorgang*",
  "name": "Bundestag Vorgang API",
  "methods": ["GET"],
  "upstream_id": "bundestag-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "search.dip.bundestag.de",
      "regex_uri": ["^/bundestag/vorgang(.*)$", "/api/v1/vorgang$1"]
    },
    "api-request-tracker": {
      "api_name": "bundestag-vorgang",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Bundestag Vorgang route"

# Bundestag Drucksache (Documents) route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/bundestag-drucksache '{
  "uri": "/bundestag/drucksache*",
  "name": "Bundestag Drucksache API",
  "methods": ["GET"],
  "upstream_id": "bundestag-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "search.dip.bundestag.de",
      "regex_uri": ["^/bundestag/drucksache(.*)$", "/api/v1/drucksache$1"]
    },
    "api-request-tracker": {
      "api_name": "bundestag-drucksache",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Bundestag Drucksache route"

# Bundestag Person (Members) route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/bundestag-person '{
  "uri": "/bundestag/person*",
  "name": "Bundestag Person API",
  "methods": ["GET"],
  "upstream_id": "bundestag-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "search.dip.bundestag.de",
      "regex_uri": ["^/bundestag/person(.*)$", "/api/v1/person$1"]
    },
    "api-request-tracker": {
      "api_name": "bundestag-person",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Bundestag Person route"

# Bundestag Plenarprotokoll (Plenary Transcripts) route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/bundestag-plenarprotokoll '{
  "uri": "/bundestag/plenarprotokoll*",
  "name": "Bundestag Plenarprotokoll API",
  "methods": ["GET"],
  "upstream_id": "bundestag-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "search.dip.bundestag.de",
      "regex_uri": ["^/bundestag/plenarprotokoll(.*)$", "/api/v1/plenarprotokoll$1"]
    },
    "api-request-tracker": {
      "api_name": "bundestag-plenarprotokoll",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Bundestag Plenarprotokoll route"

# Bundestag Aktivitaet (Activities) route
docker exec policiytracker-etcd etcdctl --endpoints=http://localhost:2379 put /apisix/routes/bundestag-aktivitaet '{
  "uri": "/bundestag/aktivitaet*",
  "name": "Bundestag Aktivitaet API",
  "methods": ["GET"],
  "upstream_id": "bundestag-upstream",
  "plugins": {
    "proxy-rewrite": {
      "scheme": "https",
      "host": "search.dip.bundestag.de",
      "regex_uri": ["^/bundestag/aktivitaet(.*)$", "/api/v1/aktivitaet$1"]
    },
    "api-request-tracker": {
      "api_name": "bundestag-aktivitaet",
      "enabled": true,
      "log_debug": false
    },
    "limit-req": {
      "rate": 5,
      "burst": 3,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429
    }
  },
  "status": 1
}'

echo "✓ Created Bundestag Aktivitaet route"

echo ""
echo "============================================================"
echo "✅ All external API routes configured successfully!"
echo "============================================================"
echo ""
echo "Available routes via APISIX gateway (http://localhost:9080):"
echo ""
echo "  Exa.ai:"
echo "    POST /exa/search       → api.exa.ai/search"
echo "    POST /exa/contents     → api.exa.ai/contents"
echo ""
echo "  DPA:"
echo "    GET/POST /dpa/articles/* → article-retriever.iq.dpa-ai-hub.de/articles/*"
echo ""
echo "  Bundestag DIP:"
echo "    GET /bundestag/vorgang*         → search.dip.bundestag.de/api/v1/vorgang"
echo "    GET /bundestag/drucksache*      → search.dip.bundestag.de/api/v1/drucksache"
echo "    GET /bundestag/person*          → search.dip.bundestag.de/api/v1/person"
echo "    GET /bundestag/plenarprotokoll* → search.dip.bundestag.de/api/v1/plenarprotokoll"
echo "    GET /bundestag/aktivitaet*      → search.dip.bundestag.de/api/v1/aktivitaet"
echo ""
echo "Note: Clients must still provide API keys in headers:"
echo "  - Exa: x-api-key"
echo "  - DPA: X-API-Key"
echo "  - Bundestag: Authorization"
echo ""
