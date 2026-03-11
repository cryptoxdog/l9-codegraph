# ============================================================================
# tests/unit/test_chassis_app.py
# ============================================================================
"""
Unit tests for chassis/app.py — FastAPI factory and endpoints.
Target Coverage: 85%+

Tests the FastAPI application factory, Pydantic request/response models,
POST /v1/execute endpoint routing, and GET /v1/health endpoint.

Architecture Note:
    chassis/app.py owns HTTP (FastAPI). It imports:
      - chassis.actions.execute_action  (action router)
      - engine.config.loader.DomainPackLoader
      - engine.config.settings.settings
      - engine.graph.driver.GraphDriver
      - engine.handlers.init_dependencies
    The lifespan context manager initialises GraphDriver + DomainPackLoader
    and calls init_dependencies(). All three must be mocked for unit tests.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from chassis.app import ExecuteRequest, ExecuteResponse


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_graph_driver():
    """Mock GraphDriver that satisfies the lifespan connect/close cycle."""
    driver = AsyncMock()
    driver.connect = AsyncMock()
    driver.close = AsyncMock()
    return driver


@pytest.fixture
def mock_domain_loader():
    """Mock DomainPackLoader for testing without filesystem."""
    loader = MagicMock()
    loader.list_domains = MagicMock(return_value=["plastics_recycling"])
    return loader


@pytest.fixture
def test_app(mock_graph_driver, mock_domain_loader):
    """Create a fully-mocked FastAPI app via create_app().

    Patches the three lifespan dependencies so no real Neo4j,
    filesystem, or engine init occurs.
    """
    with (
        patch("chassis.app.GraphDriver", return_value=mock_graph_driver),
        patch("chassis.app.DomainPackLoader", return_value=mock_domain_loader),
        patch("chassis.app.init_dependencies"),
    ):
        from chassis.app import create_app

        yield create_app()


@pytest.fixture
def test_client(test_app):
    """Sync TestClient for non-async tests."""
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        yield client


# ============================================================================
# PYDANTIC MODEL TESTS
# ============================================================================


@pytest.mark.unit
class TestExecuteRequest:
    """Test ExecuteRequest Pydantic model validation."""

    def test_valid_minimal_input(self) -> None:
        """ExecuteRequest accepts action + tenant with defaults."""
        req = ExecuteRequest(action="match", tenant="acme-corp")
        assert req.action == "match"
        assert req.tenant == "acme-corp"
        assert req.payload == {}
        assert req.trace_id is None

    def test_valid_full_input(self) -> None:
        """ExecuteRequest accepts all fields including optional trace_id."""
        req = ExecuteRequest(
            action="sync",
            tenant="t1",
            payload={"entities": [{"id": "e1"}]},
            trace_id="tr_abc123",
        )
        assert req.action == "sync"
        assert req.payload == {"entities": [{"id": "e1"}]}
        assert req.trace_id == "tr_abc123"

    def test_missing_action_raises(self) -> None:
        """ExecuteRequest rejects missing action field."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExecuteRequest(tenant="t1")

    def test_missing_tenant_raises(self) -> None:
        """ExecuteRequest rejects missing tenant field."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExecuteRequest(action="match")

    def test_payload_defaults_to_empty_dict(self) -> None:
        """ExecuteRequest defaults payload to empty dict when omitted."""
        req = ExecuteRequest(action="health", tenant="t1")
        assert isinstance(req.payload, dict)
        assert len(req.payload) == 0


@pytest.mark.unit
class TestExecuteResponse:
    """Test ExecuteResponse Pydantic model validation."""

    def test_valid_response(self) -> None:
        """ExecuteResponse accepts all required fields."""
        resp = ExecuteResponse(
            status="success",
            action="match",
            tenant="t1",
            data={"candidates": []},
            meta={"trace_id": "tr_1", "execution_ms": 42.0},
        )
        assert resp.status == "success"
        assert resp.action == "match"
        assert resp.data == {"candidates": []}

    def test_missing_data_raises(self) -> None:
        """ExecuteResponse rejects missing data field."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExecuteResponse(status="success", action="match", tenant="t1", meta={})

    def test_missing_meta_raises(self) -> None:
        """ExecuteResponse rejects missing meta field."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExecuteResponse(status="success", action="match", tenant="t1", data={})


# ============================================================================
# CREATE_APP FACTORY TESTS
# ============================================================================


@pytest.mark.unit
class TestCreateApp:
    """Test create_app() factory function."""

    def test_returns_fastapi_instance(self, test_app) -> None:
        """create_app() returns a FastAPI application."""
        from fastapi import FastAPI

        assert isinstance(test_app, FastAPI)

    def test_app_title(self, test_app) -> None:
        """Application title matches L9 Graph Cognitive Engine."""
        assert test_app.title == "L9 Graph Cognitive Engine"

    def test_app_version(self, test_app) -> None:
        """Application version matches expected value."""
        assert test_app.version == "1.1.0"

    def test_cors_middleware_applied_when_origins_set(
        self, mock_graph_driver, mock_domain_loader
    ) -> None:
        """CORSMiddleware is added when settings.cors_origins is non-empty."""
        mock_settings = MagicMock()
        mock_settings.cors_origins = ["http://localhost:3000"]
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_username = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.domains_root = "/tmp/domains"

        with (
            patch("chassis.app.GraphDriver", return_value=mock_graph_driver),
            patch("chassis.app.DomainPackLoader", return_value=mock_domain_loader),
            patch("chassis.app.init_dependencies"),
            patch("chassis.app.settings", mock_settings),
        ):
            from chassis.app import create_app

            app = create_app()
            middleware_classes = [m.cls.__name__ for m in app.user_middleware]
            assert "CORSMiddleware" in middleware_classes

    def test_no_cors_middleware_when_origins_empty(self, test_app) -> None:
        """CORSMiddleware is NOT added when settings.cors_origins is empty."""
        middleware_classes = [m.cls.__name__ for m in test_app.user_middleware]
        assert "CORSMiddleware" not in middleware_classes

    def test_routes_registered(self, test_app) -> None:
        """App has /v1/execute and /v1/health routes."""
        route_paths = [r.path for r in test_app.routes]
        assert "/v1/execute" in route_paths
        assert "/v1/health" in route_paths


# ============================================================================
# POST /v1/execute ENDPOINT TESTS
# ============================================================================


@pytest.mark.unit
class TestExecuteEndpoint:
    """Test POST /v1/execute endpoint routing and error handling."""

    def test_execute_success(self, test_client) -> None:
        """POST /v1/execute returns 200 with ExecuteResponse on success."""
        mock_result = {
            "status": "success",
            "action": "health",
            "tenant": "t1",
            "data": {"status": "healthy"},
            "meta": {
                "trace_id": "tr_1",
                "execution_ms": 5.0,
                "version": "1.1.0",
                "timestamp": "2026-03-04T12:00:00Z",
            },
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = test_client.post(
                "/v1/execute",
                json={"action": "health", "tenant": "t1", "payload": {}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["action"] == "health"
        assert data["tenant"] == "t1"

    def test_execute_with_trace_id(self, test_client) -> None:
        """POST /v1/execute forwards trace_id when provided."""
        mock_result = {
            "status": "success",
            "action": "match",
            "tenant": "t1",
            "data": {"candidates": []},
            "meta": {
                "trace_id": "custom_tr",
                "execution_ms": 10.0,
                "version": "1.1.0",
                "timestamp": "2026-03-04T12:00:00Z",
            },
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_exec:
            resp = test_client.post(
                "/v1/execute",
                json={
                    "action": "match",
                    "tenant": "t1",
                    "payload": {"query": {}},
                    "trace_id": "custom_tr",
                },
            )
        assert resp.status_code == 200
        call_kwargs = mock_exec.call_args
        assert call_kwargs.kwargs.get("trace_id") == "custom_tr" or (
            call_kwargs.args and "custom_tr" in str(call_kwargs)
        )

    def test_execute_invalid_payload_returns_422(self, test_client) -> None:
        """POST /v1/execute with missing required fields returns 422."""
        resp = test_client.post(
            "/v1/execute",
            json={"bad": "data"},
        )
        assert resp.status_code == 422

    def test_execute_empty_body_returns_422(self, test_client) -> None:
        """POST /v1/execute with empty body returns 422."""
        resp = test_client.post("/v1/execute", json={})
        assert resp.status_code == 422

    def test_execute_handler_runtime_error_returns_500(self, test_client) -> None:
        """POST /v1/execute returns 500 on unhandled handler exception."""
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Neo4j connection lost"),
        ):
            resp = test_client.post(
                "/v1/execute",
                json={"action": "match", "tenant": "t1", "payload": {}},
            )
        assert resp.status_code == 500

    def test_execute_value_error_returns_400(self, test_client) -> None:
        """POST /v1/execute returns 400 on ValueError (unknown action)."""
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            side_effect=ValueError("Unknown action: 'bogus'"),
        ):
            resp = test_client.post(
                "/v1/execute",
                json={"action": "bogus", "tenant": "t1", "payload": {}},
            )
        assert resp.status_code == 400
        assert "Unknown action" in resp.json()["detail"]

    def test_execute_failed_validation_returns_422(self, test_client) -> None:
        """POST /v1/execute returns 422 when chassis status=failed + validation error."""
        mock_result = {
            "status": "failed",
            "action": "match",
            "tenant": "t1",
            "data": {"error": "Validation error in payload"},
            "meta": {
                "trace_id": "tr_x",
                "execution_ms": 3.0,
                "version": "1.1.0",
                "timestamp": "2026-03-04T12:00:00Z",
            },
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = test_client.post(
                "/v1/execute",
                json={"action": "match", "tenant": "t1", "payload": {}},
            )
        assert resp.status_code == 422

    def test_execute_failed_invalid_returns_422(self, test_client) -> None:
        """POST /v1/execute returns 422 when error contains 'invalid'."""
        mock_result = {
            "status": "failed",
            "action": "sync",
            "tenant": "t1",
            "data": {"error": "Invalid entity schema"},
            "meta": {
                "trace_id": "tr_y",
                "execution_ms": 2.0,
                "version": "1.1.0",
                "timestamp": "2026-03-04T12:00:00Z",
            },
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = test_client.post(
                "/v1/execute",
                json={"action": "sync", "tenant": "t1", "payload": {}},
            )
        assert resp.status_code == 422
        assert "Invalid" in resp.json()["detail"]

    def test_execute_failed_generic_returns_500(self, test_client) -> None:
        """POST /v1/execute returns 500 when status=failed without validation keyword."""
        mock_result = {
            "status": "failed",
            "action": "match",
            "tenant": "t1",
            "data": {"error": "Database connection refused"},
            "meta": {
                "trace_id": "tr_z",
                "execution_ms": 100.0,
                "version": "1.1.0",
                "timestamp": "2026-03-04T12:00:00Z",
            },
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = test_client.post(
                "/v1/execute",
                json={"action": "match", "tenant": "t1", "payload": {}},
            )
        assert resp.status_code == 500
        assert "Database connection refused" in resp.json()["detail"]


# ============================================================================
# GET /v1/health ENDPOINT TESTS
# ============================================================================


@pytest.mark.unit
class TestHealthEndpoint:
    """Test GET /v1/health endpoint."""

    def test_health_returns_200_when_healthy(self, test_client) -> None:
        """GET /v1/health returns 200 when engine reports healthy."""
        mock_result = {
            "status": "success",
            "action": "health",
            "tenant": "default",
            "data": {"status": "healthy"},
            "meta": {"trace_id": "health_abc"},
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = test_client.get("/v1/health")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "healthy"

    def test_health_returns_503_when_degraded(self, test_client) -> None:
        """GET /v1/health returns 503 when engine is degraded."""
        mock_result = {
            "status": "success",
            "action": "health",
            "tenant": "default",
            "data": {"status": "degraded"},
            "meta": {},
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = test_client.get("/v1/health")
        assert resp.status_code == 503

    def test_health_returns_503_when_unhealthy(self, test_client) -> None:
        """GET /v1/health returns 503 when engine is unhealthy."""
        mock_result = {
            "status": "success",
            "action": "health",
            "tenant": "default",
            "data": {"status": "unhealthy"},
            "meta": {},
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = test_client.get("/v1/health")
        assert resp.status_code == 503

    def test_health_returns_503_on_exception(self, test_client) -> None:
        """GET /v1/health returns 503 on unhandled exception."""
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Neo4j down"),
        ):
            resp = test_client.get("/v1/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["error"] == "health_check_failed"

    def test_health_with_tenant_query_param(self, test_client) -> None:
        """GET /v1/health?tenant=acme passes tenant to execute_action."""
        mock_result = {
            "status": "success",
            "action": "health",
            "tenant": "acme",
            "data": {"status": "healthy"},
            "meta": {},
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_exec:
            resp = test_client.get("/v1/health?tenant=acme")
        assert resp.status_code == 200
        call_kwargs = mock_exec.call_args
        assert call_kwargs.kwargs.get("tenant") == "acme" or (
            len(call_kwargs.args) > 0 and "acme" in str(call_kwargs)
        )

    def test_health_default_tenant(self, test_client) -> None:
        """GET /v1/health without tenant param defaults to 'default'."""
        mock_result = {
            "status": "success",
            "action": "health",
            "tenant": "default",
            "data": {"status": "healthy"},
            "meta": {},
        }
        with patch(
            "chassis.app.execute_action",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_exec:
            resp = test_client.get("/v1/health")
        assert resp.status_code == 200
        call_kwargs = mock_exec.call_args
        assert call_kwargs.kwargs.get("tenant") == "default" or (
            len(call_kwargs.args) > 0 and "default" in str(call_kwargs)
        )


# ============================================================================
# LIFESPAN TESTS
# ============================================================================


@pytest.mark.unit
class TestLifespan:
    """Test lifespan context manager behaviour."""

    def test_lifespan_connects_graph_driver(self, test_client, mock_graph_driver) -> None:
        """Lifespan calls graph_driver.connect() on startup."""
        mock_graph_driver.connect.assert_awaited_once()

    def test_lifespan_initialises_dependencies(self) -> None:
        """Lifespan calls init_dependencies with driver and loader."""
        mock_driver = AsyncMock()
        mock_driver.connect = AsyncMock()
        mock_driver.close = AsyncMock()
        mock_loader = MagicMock()

        with (
            patch("chassis.app.GraphDriver", return_value=mock_driver),
            patch("chassis.app.DomainPackLoader", return_value=mock_loader),
            patch("chassis.app.init_dependencies") as mock_init,
        ):
            from chassis.app import create_app
            from fastapi.testclient import TestClient

            app = create_app()
            with TestClient(app):
                pass
            mock_init.assert_called_once_with(mock_driver, mock_loader)
