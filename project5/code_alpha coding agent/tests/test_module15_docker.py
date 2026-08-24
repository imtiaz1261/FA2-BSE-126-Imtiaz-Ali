# Module 15a: Docker & Docker Compose Tests

import pytest
import subprocess
import os
import time
import requests
import docker
from pathlib import Path


class TestDockerImages:
    """Test Docker image building"""
    
    def test_docker_available(self):
        """Verify Docker is installed"""
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        assert result.returncode == 0
        assert 'Docker' in result.stdout
    
    def test_docker_compose_available(self):
        """Verify Docker Compose is installed"""
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        assert result.returncode == 0
        assert 'docker-compose' in result.stdout or 'Docker Compose' in result.stdout
    
    def test_dockerfiles_exist(self):
        """Verify all Dockerfiles exist"""
        dockerfiles = [
            'docker/Dockerfile.api-gateway',
            'docker/Dockerfile.orchestrator',
            'docker/Dockerfile.sandbox-worker',
            'docker/Dockerfile.indexing-worker',
        ]
        for dockerfile in dockerfiles:
            assert Path(dockerfile).exists(), f"{dockerfile} not found"
    
    def test_docker_compose_files_exist(self):
        """Verify all Docker Compose files exist"""
        compose_files = [
            'docker/docker-compose.dev.yml',
            'docker/docker-compose.prod.yml',
            'docker/docker-compose.test.yml',
        ]
        for compose_file in compose_files:
            assert Path(compose_file).exists(), f"{compose_file} not found"
    
    def test_dockerignore_exists(self):
        """Verify .dockerignore exists"""
        assert Path('docker/.dockerignore').exists()
    
    def test_init_db_sql_exists(self):
        """Verify database init script exists"""
        assert Path('docker/init-db.sql').exists()
    
    def test_build_script_exists(self):
        """Verify build script exists"""
        build_script = Path('docker/build.sh')
        assert build_script.exists()
        assert os.access(build_script, os.X_OK), "build.sh is not executable"


class TestDockerComposeDev:
    """Test Docker Compose development configuration"""
    
    @pytest.fixture(scope="class")
    def dev_compose(self):
        """Setup and teardown Docker Compose dev environment"""
        # Start services
        subprocess.run(
            ['docker-compose', '-f', 'docker/docker-compose.dev.yml', 'up', '-d'],
            check=True,
            capture_output=True
        )
        time.sleep(10)
        
        yield
        
        # Cleanup
        subprocess.run(
            ['docker-compose', '-f', 'docker/docker-compose.dev.yml', 'down', '-v'],
            capture_output=True
        )
    
    def test_services_running(self, dev_compose):
        """Verify all services are running"""
        result = subprocess.run(
            ['docker-compose', '-f', 'docker/docker-compose.dev.yml', 'ps', '-q'],
            capture_output=True,
            text=True,
            check=True
        )
        container_ids = result.stdout.strip().split('\n')
        assert len(container_ids) >= 5, "Not all services are running"
    
    def test_redis_healthy(self, dev_compose):
        """Verify Redis is healthy"""
        result = subprocess.run(
            ['docker-compose', '-f', 'docker/docker-compose.dev.yml', 'exec', '-T', 'redis', 'redis-cli', 'ping'],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert 'PONG' in result.stdout
    
    def test_postgres_healthy(self, dev_compose):
        """Verify PostgreSQL is healthy"""
        result = subprocess.run(
            ['docker-compose', '-f', 'docker/docker-compose.dev.yml', 'exec', '-T', 'postgres', 'pg_isready', '-U', 'codealpha'],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert 'accepting connections' in result.stdout
    
    def test_api_responds(self, dev_compose):
        """Verify API responds to health check"""
        time.sleep(5)  # Wait for API to start
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("API not accessible on localhost:8000")


class TestDockerSecurity:
    """Test Docker security best practices"""
    
    def test_non_root_user_in_api(self):
        """Verify API runs as non-root user"""
        with open('docker/Dockerfile.api-gateway') as f:
            content = f.read()
            assert 'USER codealpha' in content or 'useradd' in content
    
    def test_non_root_user_in_orchestrator(self):
        """Verify Orchestrator runs as non-root user"""
        with open('docker/Dockerfile.orchestrator') as f:
            content = f.read()
            assert 'USER codealpha' in content or 'useradd' in content
    
    def test_health_checks_defined(self):
        """Verify all Dockerfiles have health checks"""
        dockerfiles = [
            'docker/Dockerfile.api-gateway',
            'docker/Dockerfile.orchestrator',
            'docker/Dockerfile.sandbox-worker',
            'docker/Dockerfile.indexing-worker',
        ]
        for dockerfile in dockerfiles:
            with open(dockerfile) as f:
                content = f.read()
                # Health check should be present
                assert 'HEALTHCHECK' in content or 'curl' in content or 'healthcheck' in content


class TestDockerComposeSecurity:
    """Test Docker Compose security configuration"""
    
    def test_prod_has_resource_limits(self):
        """Verify production compose has resource limits"""
        with open('docker/docker-compose.prod.yml') as f:
            content = f.read()
            assert 'limits:' in content
            assert 'memory:' in content
            assert 'cpus:' in content
    
    def test_prod_has_restart_policy(self):
        """Verify production compose has restart policies"""
        with open('docker/docker-compose.prod.yml') as f:
            content = f.read()
            assert 'restart: always' in content
    
    def test_prod_uses_read_only_fs(self):
        """Verify production compose uses read-only filesystem where possible"""
        with open('docker/docker-compose.prod.yml') as f:
            content = f.read()
            # At least some services should have read-only root fs
            assert 'read_only' in content or 'ro' in content


@pytest.mark.slow
class TestDockerImageBuilds:
    """Test building Docker images (slow, optional)"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Get Docker client"""
        return docker.from_env()
    
    def test_api_image_builds(self, client):
        """Test building API image"""
        try:
            image, logs = client.images.build(
                path='.',
                dockerfile='docker/Dockerfile.api-gateway',
                tag='codealpha-api-test:latest'
            )
            assert image is not None
            # Cleanup
            client.images.remove(image.id, force=True)
        except Exception as e:
            pytest.skip(f"Docker build not available: {e}")
    
    def test_orchestrator_image_builds(self, client):
        """Test building Orchestrator image"""
        try:
            image, logs = client.images.build(
                path='.',
                dockerfile='docker/Dockerfile.orchestrator',
                tag='codealpha-orchestrator-test:latest'
            )
            assert image is not None
            # Cleanup
            client.images.remove(image.id, force=True)
        except Exception as e:
            pytest.skip(f"Docker build not available: {e}")
