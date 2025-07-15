"""
Unit tests for SAP BTP client.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime, timedelta

from open_logistics.infrastructure.external.sap_btp_client import SAPBTPClient
from open_logistics.core.config import get_settings


class TestSAPBTPClient:
    """Tests for the SAP BTP client."""

    def setup_method(self):
        """Setup test fixtures."""
        self.client = SAPBTPClient()

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""
        assert self.client.settings is not None
        assert self.client.client is not None
        assert self.client.access_token is None
        assert self.client.token_expires_at is None

    @pytest.mark.asyncio
    async def test_authenticate_missing_client_id(self):
        """Test authentication with missing client ID."""
        with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_ID', None):
            with pytest.raises(ValueError, match="SAP BTP client ID is not configured"):
                await self.client.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_missing_client_secret(self):
        """Test authentication with missing client secret."""
        with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_ID', 'test_id'):
            with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_SECRET', None):
                with pytest.raises(ValueError, match="SAP BTP client secret is not configured"):
                    await self.client.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication."""
        with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_ID', 'test_id'):
            with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_SECRET', 'test_secret'):
                with patch.object(self.client.settings.sap_btp, 'BTP_AUTH_URL', 'https://auth.example.com'):
                    
                    # Mock HTTP response
                    mock_response = MagicMock()
                    mock_response.json.return_value = {
                        "access_token": "test_token",
                        "expires_in": 3600
                    }
                    mock_response.raise_for_status.return_value = None
                    
                    with patch.object(self.client.client, 'post', return_value=mock_response):
                        token = await self.client.authenticate()
                        
                        assert token == "test_token"
                        assert self.client.access_token == "test_token"
                        assert self.client.token_expires_at is not None

    @pytest.mark.asyncio
    async def test_authenticate_http_error(self):
        """Test authentication with HTTP error."""
        with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_ID', 'test_id'):
            with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_SECRET', 'test_secret'):
                
                mock_response = MagicMock()
                mock_response.raise_for_status.side_effect = httpx.HTTPError("Auth failed")
                
                with patch.object(self.client.client, 'post', return_value=mock_response):
                    with pytest.raises(httpx.HTTPError):
                        await self.client.authenticate()

    @pytest.mark.asyncio
    async def test_deploy_ai_model_success(self):
        """Test successful AI model deployment."""
        self.client.access_token = "test_token"
        
        model_config = {
            "configuration_id": "config_123",
            "model_name": "supply_chain_optimizer",
            "model_version": "1.0.0",
            "parameters": {"temperature": 0.7}
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "deployment_123",
            "status": "deployed",
            "model_name": "supply_chain_optimizer"
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                result = await self.client.deploy_ai_model(model_config)
                
                assert result["id"] == "deployment_123"
                assert result["status"] == "deployed"

    @pytest.mark.asyncio
    async def test_deploy_ai_model_error(self):
        """Test AI model deployment with error."""
        self.client.access_token = "test_token"
        
        model_config = {
            "configuration_id": "config_123",
            "model_name": "supply_chain_optimizer"
        }
        
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Deployment failed")
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                with pytest.raises(httpx.HTTPError):
                    await self.client.deploy_ai_model(model_config)

    @pytest.mark.asyncio
    async def test_run_inference_success(self):
        """Test successful inference execution."""
        deployment_id = "deployment_123"
        input_data = {"inventory": {"missiles": 100}}
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "outputs": {"optimized_plan": "test_plan"},
            "inference_id": "inference_456"
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                result = await self.client.run_inference(deployment_id, input_data)
                
                assert result["outputs"]["optimized_plan"] == "test_plan"
                assert result["inference_id"] == "inference_456"

    @pytest.mark.asyncio
    async def test_run_inference_error(self):
        """Test inference execution with error."""
        deployment_id = "deployment_123"
        input_data = {"inventory": {"missiles": 100}}
        
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Inference failed")
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                with pytest.raises(httpx.HTTPError):
                    await self.client.run_inference(deployment_id, input_data)

    @pytest.mark.asyncio
    async def test_publish_event_success(self):
        """Test successful event publishing."""
        event_type = "supply_chain_optimized"
        event_data = {"optimization_id": "opt_123", "status": "completed"}
        
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                result = await self.client.publish_event(event_type, event_data)
                
                assert result is True

    @pytest.mark.asyncio
    async def test_publish_event_error(self):
        """Test event publishing with error."""
        event_type = "supply_chain_optimized"
        event_data = {"optimization_id": "opt_123"}
        
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Event publishing failed")
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                result = await self.client.publish_event(event_type, event_data)
                
                assert result is False

    @pytest.mark.asyncio
    async def test_query_hana_cloud_success(self):
        """Test successful HANA Cloud query."""
        query = "SELECT * FROM inventory WHERE quantity > 50"
        parameters = {"min_quantity": 50}
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"item": "missiles", "quantity": 100},
                {"item": "radar", "quantity": 75}
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                result = await self.client.query_hana_cloud(query, parameters)
                
                assert len(result) == 2
                assert result[0]["item"] == "missiles"
                assert result[1]["item"] == "radar"

    @pytest.mark.asyncio
    async def test_query_hana_cloud_error(self):
        """Test HANA Cloud query with error."""
        query = "SELECT * FROM inventory"
        
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Query failed")
        
        with patch.object(self.client, 'authenticate', return_value="test_token"):
            with patch.object(self.client.client, 'post', return_value=mock_response):
                with pytest.raises(httpx.HTTPError):
                    await self.client.query_hana_cloud(query)

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test client cleanup."""
        with patch.object(self.client.client, 'aclose') as mock_close:
            await self.client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        with patch.object(self.client.client, 'aclose') as mock_close:
            async with self.client as client:
                assert client is self.client
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test authentication failure handling."""
        with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_ID', 'test_id'):
            with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_SECRET', 'test_secret'):
                
                mock_response = MagicMock()
                mock_response.raise_for_status.side_effect = httpx.HTTPError("Unauthorized")
                
                with patch.object(self.client.client, 'post', return_value=mock_response):
                    with pytest.raises(httpx.HTTPError):
                        await self.client.authenticate()

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_ID', 'test_id'):
            with patch.object(self.client.settings.sap_btp, 'BTP_CLIENT_SECRET', 'test_secret'):
                
                with patch.object(self.client.client, 'post', side_effect=Exception("Unexpected error")):
                    with pytest.raises(Exception, match="Unexpected error"):
                        await self.client.authenticate()


# Additional tests to ensure all methods are covered
@pytest.mark.asyncio
async def test_authenticate_success():
    """Test successful authentication."""
    client = SAPBTPClient()
    
    with patch.object(client.settings.sap_btp, 'BTP_CLIENT_ID', 'test_id'):
        with patch.object(client.settings.sap_btp, 'BTP_CLIENT_SECRET', 'test_secret'):
            
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 3600
            }
            mock_response.raise_for_status.return_value = None
            
            with patch.object(client.client, 'post', return_value=mock_response):
                token = await client.authenticate()
                assert token == "test_token"


@pytest.mark.asyncio
async def test_authenticate_failure():
    """Test authentication failure."""
    client = SAPBTPClient()
    
    with patch.object(client.settings.sap_btp, 'BTP_CLIENT_ID', 'test_id'):
        with patch.object(client.settings.sap_btp, 'BTP_CLIENT_SECRET', 'test_secret'):
            
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPError("Auth failed")
            
            with patch.object(client.client, 'post', return_value=mock_response):
                with pytest.raises(httpx.HTTPError):
                    await client.authenticate() 