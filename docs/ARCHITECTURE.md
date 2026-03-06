# Architecture — PBM Research Agent (FastAPI)

## High-level flow

```
                    USER
                      │
                      ▼
             FastAPI (main.py)
                      │
                      ▼
              POST /api/chat or /api/chat/send
                      │
                      ▼
              ChatService.run_chat(query)
                      │
                      ▼
              LangGraph (graph/langgraph_builder)
                      │
          ┌───────────┴───────────┐
          │   DOC_TOOL (optional) │
          └───────────┬───────────┘
                      ▼
                 ROUTER
                 /     \
        DIRECT_LLM    HYBRID_RAG
             │              │
             │         SQL_AGENT → SQL_GUARDRAIL → SQL_EXECUTE
             │              │
             │         REPORT → FORMATTER
             │              │
             └──────┬───────┘
                    ▼
                 JUDGE
                    │
                    ▼
                  END → AgentOutput
```

## Components

| Layer | Role |
|-------|------|
| **API** | FastAPI routes, Pydantic schemas, dependency injection (get_db, repos). |
| **Services** | `chat_service`: runs agent and returns (AgentOutput, latency_ms). `knowledge_db_service`: schema introspection and SQL execution for claims DB. |
| **Graph** | `agent_state`: TypedDict + AgentOutput. `langgraph_builder`: builds and compiles the graph, exposes `run_agent(query)`. |
| **Agents** | Stateless nodes: router, direct_llm, sql_agent, sql_guardrail_node, sql_execute_node, report, formatter, judge, doc_tool. |
| **DB** | SQLAlchemy ORM for chat (sessions, messages); repository pattern. Knowledge DB: raw SQLite (or Postgres) via `knowledge_db_service`. |

## Observability

- **Request ID**: Middleware sets or forwards `X-Request-ID`, adds to response and to logging context.
- **Latency**: Middleware logs method, path, status, and adds `X-Response-Time-Ms`.
- **Structured logging**: `request_id` and optional JSON logs (see `core/logging_config.py`).

## Scalability

- **Stateless API**: Session state in DB; scale horizontally behind a load balancer.
- **Agent execution**: Synchronous LangGraph invoke per request; for high throughput consider task queue (e.g. Celery) and polling/WebSocket for results.
- **DB**: Use PostgreSQL and connection pooling in production; keep knowledge DB read-only for analytics.

## Security

- **Config**: All secrets and URLs from environment / Pydantic Settings; no hardcoded keys.
- **Input**: Query length and session_id validated; control characters stripped (see `core/security.py`).
- **Rate limiting**: Placeholder in config; add middleware or API gateway limits in production.
