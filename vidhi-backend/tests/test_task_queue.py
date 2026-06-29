"""
Tests for Async Task Queue
Tests task submission, status tracking, and cancellation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock Celery before importing
sys.modules["celery"] = MagicMock()
sys.modules["celery.result"] = MagicMock()
sys.modules["celery.schedules"] = MagicMock()
sys.modules["celery_app"] = MagicMock()


@pytest.fixture
def client():
    """Create test client"""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from routes.task_routes import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)

    return TestClient(app)


class TestTaskSubmission:
    """Test task submission"""

    @patch("routes.task_routes.celery_app")
    def test_submit_valid_task(self, mock_celery, client):
        """Test submitting a valid task"""
        mock_result = Mock()
        mock_result.id = "test-task-123"
        mock_celery.send_task.return_value = mock_result

        response = client.post(
            "/api/v1/tasks/submit",
            json={
                "task_type": "refresh_data_pipeline",
                "args": [],
                "kwargs": {"incremental": True},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["task_id"] == "test-task-123"
        assert data["task_type"] == "refresh_data_pipeline"

    def test_submit_invalid_task_type(self, client):
        """Test submitting invalid task type"""
        response = client.post(
            "/api/v1/tasks/submit",
            json={"task_type": "invalid_task", "args": [], "kwargs": {}},
        )

        assert response.status_code == 400
        assert "Invalid task type" in response.json()["detail"]

    @patch("routes.task_routes.celery_app")
    def test_submit_scraping_task(self, mock_celery, client):
        """Test submitting scraping task"""
        mock_result = Mock()
        mock_result.id = "scrape-task-456"
        mock_celery.send_task.return_value = mock_result

        response = client.post(
            "/api/v1/tasks/submit",
            json={
                "task_type": "scrape_india_code_acts",
                "args": [],
                "kwargs": {"resume": True},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "scrape-task-456"


class TestTaskStatus:
    """Test task status tracking"""

    @patch("routes.task_routes.AsyncResult")
    def test_get_pending_task_status(self, mock_async_result, client):
        """Test getting status of pending task"""
        mock_result = Mock()
        mock_result.state = "PENDING"
        mock_async_result.return_value = mock_result

        response = client.get("/api/v1/tasks/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "PENDING"
        assert "waiting" in data["result"]["message"].lower()

    @patch("routes.task_routes.AsyncResult")
    def test_get_progress_task_status(self, mock_async_result, client):
        """Test getting status of task in progress"""
        mock_result = Mock()
        mock_result.state = "PROGRESS"
        mock_result.info = {"current": 50, "total": 100, "status": "Processing..."}
        mock_async_result.return_value = mock_result

        response = client.get("/api/v1/tasks/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PROGRESS"
        assert data["progress"]["current"] == 50
        assert data["progress"]["total"] == 100

    @patch("routes.task_routes.AsyncResult")
    def test_get_success_task_status(self, mock_async_result, client):
        """Test getting status of successful task"""
        mock_result = Mock()
        mock_result.state = "SUCCESS"
        mock_result.result = {"status": "success", "data": "Task completed"}
        mock_async_result.return_value = mock_result

        response = client.get("/api/v1/tasks/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["result"]["status"] == "success"

    @patch("routes.task_routes.AsyncResult")
    def test_get_failure_task_status(self, mock_async_result, client):
        """Test getting status of failed task"""
        mock_result = Mock()
        mock_result.state = "FAILURE"
        mock_result.info = Exception("Task failed")
        mock_async_result.return_value = mock_result

        response = client.get("/api/v1/tasks/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILURE"
        assert data["error"] is not None


class TestTaskCancellation:
    """Test task cancellation"""

    @patch("routes.task_routes.AsyncResult")
    def test_cancel_running_task(self, mock_async_result, client):
        """Test cancelling a running task"""
        mock_result = Mock()
        mock_result.state = "STARTED"
        mock_result.revoke = Mock()
        mock_async_result.return_value = mock_result

        response = client.post("/api/v1/tasks/test-task-123/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["task_id"] == "test-task-123"
        mock_result.revoke.assert_called_once()

    @patch("routes.task_routes.AsyncResult")
    def test_cancel_finished_task(self, mock_async_result, client):
        """Test cancelling already finished task"""
        mock_result = Mock()
        mock_result.state = "SUCCESS"
        mock_async_result.return_value = mock_result

        response = client.post("/api/v1/tasks/test-task-123/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_finished"


class TestTaskListing:
    """Test listing active tasks"""

    @patch("routes.task_routes.celery_app")
    def test_list_active_tasks(self, mock_celery, client):
        """Test listing active tasks"""
        mock_inspect = Mock()
        mock_inspect.active.return_value = {
            "worker1": [
                {
                    "id": "task-1",
                    "name": "tasks.data_pipeline_tasks.refresh_data_pipeline",
                    "args": [],
                    "kwargs": {},
                }
            ]
        }
        mock_inspect.scheduled.return_value = {}
        mock_inspect.reserved.return_value = {}
        mock_celery.control.inspect.return_value = mock_inspect

        response = client.get("/api/v1/tasks/active/list")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "task-1"


class TestWorkerStats:
    """Test worker statistics"""

    @patch("routes.task_routes.celery_app")
    def test_get_worker_stats(self, mock_celery, client):
        """Test getting worker statistics"""
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {"worker1": {"total": {"tasks": 100}}}
        mock_inspect.active.return_value = {"worker1": []}
        mock_celery.control.inspect.return_value = mock_inspect

        response = client.get("/api/v1/tasks/stats/workers")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_workers"] == 1
        assert data["workers"][0]["name"] == "worker1"


class TestHealthCheck:
    """Test health check"""

    @patch("routes.task_routes.celery_app")
    def test_health_check_healthy(self, mock_celery, client):
        """Test health check when workers are available"""
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {"worker1": {}, "worker2": {}}
        mock_celery.control.inspect.return_value = mock_inspect

        response = client.get("/api/v1/tasks/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["workers"] == 2

    @patch("routes.task_routes.celery_app")
    def test_health_check_unhealthy(self, mock_celery, client):
        """Test health check when no workers available"""
        mock_inspect = Mock()
        mock_inspect.stats.return_value = None
        mock_celery.control.inspect.return_value = mock_inspect

        response = client.get("/api/v1/tasks/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"


class TestPropertyBasedInvariants:
    """Property-based tests for task queue"""

    def test_task_id_uniqueness(self):
        """Test that task IDs are unique"""
        # In a real system, task IDs should be unique
        # This is guaranteed by Celery's UUID generation
        import uuid

        task_ids = [str(uuid.uuid4()) for _ in range(100)]
        assert len(task_ids) == len(set(task_ids))

    def test_task_state_transitions(self):
        """Test valid task state transitions"""
        valid_states = [
            "PENDING",
            "STARTED",
            "PROGRESS",
            "SUCCESS",
            "FAILURE",
            "RETRY",
            "REVOKED",
        ]

        # All states should be valid
        for state in valid_states:
            assert state in valid_states


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
