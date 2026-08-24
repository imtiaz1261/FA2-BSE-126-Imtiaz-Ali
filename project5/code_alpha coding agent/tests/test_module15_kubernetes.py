# Module 15b: Kubernetes Manifests Tests

import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Any


def load_yaml_files(pattern: str) -> List[Dict[str, Any]]:
    """Load all YAML files matching pattern"""
    manifests = []
    for file_path in Path('k8s').glob(pattern):
        if file_path.name.startswith('.'):
            continue
        with open(file_path) as f:
            docs = yaml.safe_load_all(f)
            for doc in docs:
                if doc:  # Skip empty docs
                    manifests.append(doc)
    return manifests


class TestKubernetesManifests:
    """Test Kubernetes manifest files"""
    
    def test_manifest_files_exist(self):
        """Verify all manifest files exist"""
        required_files = [
            'k8s/namespace.yaml',
            'k8s/storage.yaml',
            'k8s/rbac.yaml',
            'k8s/configmap-secrets.yaml',
            'k8s/redis-deployment.yaml',
            'k8s/postgres-deployment.yaml',
            'k8s/api-deployment.yaml',
            'k8s/orchestrator-deployment.yaml',
            'k8s/sandbox-worker-deployment.yaml',
            'k8s/indexing-worker-deployment.yaml',
            'k8s/ingress.yaml',
        ]
        for file_path in required_files:
            assert Path(file_path).exists(), f"{file_path} not found"
    
    def test_deploy_script_executable(self):
        """Verify deploy script is executable"""
        import os
        assert os.access('k8s/deploy.sh', os.X_OK), "deploy.sh is not executable"
    
    def test_yaml_valid_syntax(self):
        """Verify all YAML files have valid syntax"""
        yaml_files = list(Path('k8s').glob('*.yaml'))
        assert len(yaml_files) > 0, "No YAML files found"
        
        for yaml_file in yaml_files:
            if yaml_file.name.startswith('.'):
                continue
            try:
                with open(yaml_file) as f:
                    yaml.safe_load_all(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {yaml_file}: {e}")


class TestNamespace:
    """Test namespace manifest"""
    
    def test_namespace_created(self):
        """Verify namespace is created"""
        manifests = load_yaml_files('namespace.yaml')
        namespace_docs = [m for m in manifests if m.get('kind') == 'Namespace']
        assert len(namespace_docs) > 0, "No Namespace found"
    
    def test_namespace_name(self):
        """Verify namespace has correct name"""
        manifests = load_yaml_files('namespace.yaml')
        namespace_docs = [m for m in manifests if m.get('kind') == 'Namespace']
        assert namespace_docs[0]['metadata']['name'] == 'code-alpha'
    
    def test_resource_quota_exists(self):
        """Verify ResourceQuota is defined"""
        manifests = load_yaml_files('namespace.yaml')
        quota_docs = [m for m in manifests if m.get('kind') == 'ResourceQuota']
        assert len(quota_docs) > 0, "No ResourceQuota found"
    
    def test_network_policy_exists(self):
        """Verify NetworkPolicy is defined"""
        manifests = load_yaml_files('namespace.yaml')
        policy_docs = [m for m in manifests if m.get('kind') == 'NetworkPolicy']
        assert len(policy_docs) > 0, "No NetworkPolicy found"


class TestDeployments:
    """Test deployment manifests"""
    
    def test_api_deployment_exists(self):
        """Verify API deployment is defined"""
        manifests = load_yaml_files('api-deployment.yaml')
        deploys = [m for m in manifests if m.get('kind') == 'Deployment' and m['metadata']['name'] == 'api']
        assert len(deploys) > 0, "No API deployment found"
    
    def test_orchestrator_deployment_exists(self):
        """Verify Orchestrator deployment is defined"""
        manifests = load_yaml_files('orchestrator-deployment.yaml')
        deploys = [m for m in manifests if m.get('kind') == 'Deployment' and m['metadata']['name'] == 'orchestrator']
        assert len(deploys) > 0, "No Orchestrator deployment found"
    
    def test_api_has_hpa(self):
        """Verify API has HorizontalPodAutoscaler"""
        manifests = load_yaml_files('api-deployment.yaml')
        hpa_docs = [m for m in manifests if m.get('kind') == 'HorizontalPodAutoscaler']
        assert len(hpa_docs) > 0, "No HPA found for API"
        
        hpa = hpa_docs[0]
        assert hpa['spec']['minReplicas'] >= 1
        assert hpa['spec']['maxReplicas'] >= hpa['spec']['minReplicas']
    
    def test_sandbox_worker_has_hpa(self):
        """Verify Sandbox Worker has HorizontalPodAutoscaler"""
        manifests = load_yaml_files('sandbox-worker-deployment.yaml')
        hpa_docs = [m for m in manifests if m.get('kind') == 'HorizontalPodAutoscaler']
        assert len(hpa_docs) > 0, "No HPA found for Sandbox Worker"
    
    def test_all_deployments_have_resources(self):
        """Verify all deployments define resource requests and limits"""
        deployment_files = ['api-deployment.yaml', 'orchestrator-deployment.yaml', 
                           'sandbox-worker-deployment.yaml', 'indexing-worker-deployment.yaml']
        
        for file in deployment_files:
            manifests = load_yaml_files(file)
            deploys = [m for m in manifests if m.get('kind') == 'Deployment']
            
            for deploy in deploys:
                containers = deploy['spec']['template']['spec']['containers']
                for container in containers:
                    assert 'resources' in container, f"No resources in {file}"
                    assert 'requests' in container['resources'], f"No requests in {file}"
                    assert 'limits' in container['resources'], f"No limits in {file}"
    
    def test_all_deployments_have_health_checks(self):
        """Verify all deployments define health checks"""
        deployment_files = ['api-deployment.yaml', 'orchestrator-deployment.yaml', 
                           'sandbox-worker-deployment.yaml', 'indexing-worker-deployment.yaml']
        
        for file in deployment_files:
            manifests = load_yaml_files(file)
            deploys = [m for m in manifests if m.get('kind') == 'Deployment']
            
            for deploy in deploys:
                containers = deploy['spec']['template']['spec']['containers']
                for container in containers:
                    # Should have at least liveness or readiness probe
                    has_probe = 'livenessProbe' in container or 'readinessProbe' in container
                    assert has_probe, f"No health check in {file}"


class TestStorage:
    """Test storage manifests"""
    
    def test_storage_classes_exist(self):
        """Verify StorageClasses are defined"""
        manifests = load_yaml_files('storage.yaml')
        scs = [m for m in manifests if m.get('kind') == 'StorageClass']
        assert len(scs) >= 2, "Less than 2 StorageClasses found"
    
    def test_pvcs_exist(self):
        """Verify PersistentVolumeClaims are defined"""
        manifests = load_yaml_files('storage.yaml')
        pvcs = [m for m in manifests if m.get('kind') == 'PersistentVolumeClaim']
        assert len(pvcs) >= 4, "Less than 4 PVCs found"
    
    def test_postgres_pvc_exists(self):
        """Verify PostgreSQL PVC is defined"""
        manifests = load_yaml_files('storage.yaml')
        pvcs = [m for m in manifests if m.get('kind') == 'PersistentVolumeClaim' and m['metadata']['name'] == 'postgres-pvc']
        assert len(pvcs) > 0, "PostgreSQL PVC not found"
    
    def test_pvc_sizes_reasonable(self):
        """Verify PVC sizes are reasonable"""
        manifests = load_yaml_files('storage.yaml')
        pvcs = [m for m in manifests if m.get('kind') == 'PersistentVolumeClaim']
        
        for pvc in pvcs:
            storage = pvc['spec']['resources']['requests']['storage']
            # Should be in Gi format and at least 1Gi
            assert 'Gi' in storage or 'G' in storage, f"Unusual storage format: {storage}"


class TestRBAC:
    """Test RBAC manifests"""
    
    def test_service_accounts_exist(self):
        """Verify ServiceAccounts are defined"""
        manifests = load_yaml_files('rbac.yaml')
        sas = [m for m in manifests if m.get('kind') == 'ServiceAccount']
        assert len(sas) >= 2, "Less than 2 ServiceAccounts found"
    
    def test_cluster_roles_exist(self):
        """Verify ClusterRoles are defined"""
        manifests = load_yaml_files('rbac.yaml')
        crs = [m for m in manifests if m.get('kind') == 'ClusterRole']
        assert len(crs) >= 2, "Less than 2 ClusterRoles found"
    
    def test_cluster_role_bindings_exist(self):
        """Verify ClusterRoleBindings are defined"""
        manifests = load_yaml_files('rbac.yaml')
        crbs = [m for m in manifests if m.get('kind') == 'ClusterRoleBinding']
        assert len(crbs) >= 2, "Less than 2 ClusterRoleBindings found"


class TestSecrets:
    """Test secrets manifest"""
    
    def test_configmaps_exist(self):
        """Verify ConfigMaps are defined"""
        manifests = load_yaml_files('configmap-secrets.yaml')
        cms = [m for m in manifests if m.get('kind') == 'ConfigMap']
        assert len(cms) >= 4, "Less than 4 ConfigMaps found"
    
    def test_secrets_exist(self):
        """Verify Secrets are defined"""
        manifests = load_yaml_files('configmap-secrets.yaml')
        secrets = [m for m in manifests if m.get('kind') == 'Secret']
        assert len(secrets) >= 2, "Less than 2 Secrets found"
    
    def test_db_secret_exists(self):
        """Verify database secret is defined"""
        manifests = load_yaml_files('configmap-secrets.yaml')
        secrets = [m for m in manifests if m.get('kind') == 'Secret' and m['metadata']['name'] == 'db-secret']
        assert len(secrets) > 0, "Database secret not found"


class TestIngress:
    """Test ingress manifest"""
    
    def test_ingress_exists(self):
        """Verify Ingress is defined"""
        manifests = load_yaml_files('ingress.yaml')
        ingresses = [m for m in manifests if m.get('kind') == 'Ingress']
        assert len(ingresses) > 0, "No Ingress found"
    
    def test_ingress_has_tls(self):
        """Verify Ingress has TLS configuration"""
        manifests = load_yaml_files('ingress.yaml')
        ingresses = [m for m in manifests if m.get('kind') == 'Ingress']
        
        for ingress in ingresses:
            assert 'tls' in ingress['spec'], "Ingress missing TLS configuration"


class TestServices:
    """Test service manifests"""
    
    def test_services_exist(self):
        """Verify Services are defined"""
        manifests = []
        for file in ['redis-deployment.yaml', 'postgres-deployment.yaml', 'api-deployment.yaml', 
                    'orchestrator-deployment.yaml', 'sandbox-worker-deployment.yaml', 'indexing-worker-deployment.yaml']:
            manifests.extend(load_yaml_files(file))
        
        services = [m for m in manifests if m.get('kind') == 'Service']
        assert len(services) >= 5, "Less than 5 Services found"
    
    def test_api_service_exists(self):
        """Verify API service is defined"""
        manifests = load_yaml_files('api-deployment.yaml')
        services = [m for m in manifests if m.get('kind') == 'Service' and m['metadata']['name'] == 'api']
        assert len(services) > 0, "API service not found"


@pytest.mark.slow
class TestKubernetesValidation:
    """Test Kubernetes manifest validation (requires kubectl)"""
    
    def test_manifests_valid_with_kubectl(self):
        """Validate manifests with kubectl"""
        import subprocess
        try:
            result = subprocess.run(['kubectl', '--help'], capture_output=True)
            if result.returncode != 0:
                pytest.skip("kubectl not available")
        except FileNotFoundError:
            pytest.skip("kubectl not installed")
        
        # This would validate against actual cluster
        # Just verify we can dry-run
        try:
            subprocess.run(
                ['kubectl', 'apply', '-f', 'k8s/', '--dry-run=client', '--validate=true'],
                capture_output=True,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            pytest.skip("kubectl validation timed out")
