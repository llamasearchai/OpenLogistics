"""
Comprehensive tests for Agent Manager.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from open_logistics.application.agents.agent_manager import (
    AgentManager, AgentConfig, AgentStatus
)


class TestAgentConfig:
    """Test AgentConfig model."""
    
    def test_agent_config_creation(self):
        """Test creating an agent configuration."""
        config = AgentConfig(
            name="test-agent",
            type="test",
            model="gpt-4",
            temperature=0.5,
            max_tokens=1000,
            system_prompt="Test prompt",
            tools=["tool1", "tool2"],
            enabled=True
        )
        
        assert config.name == "test-agent"
        assert config.type == "test"
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.system_prompt == "Test prompt"
        assert config.tools == ["tool1", "tool2"]
        assert config.enabled is True
    
    def test_agent_config_defaults(self):
        """Test agent configuration defaults."""
        config = AgentConfig(
            name="test", 
            type="test",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="",
            enabled=True
        )
        
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.system_prompt == ""
        assert config.tools == []
        assert config.enabled is True


class TestAgentStatus:
    """Test AgentStatus model."""
    
    def test_agent_status_creation(self):
        """Test creating agent status."""
        now = datetime.now()
        status = AgentStatus(
            name="test-agent",
            type="test",
            status="active",
            last_activity=now,
            messages_processed=10,
            errors=1,
            uptime_seconds=3600.0
        )
        
        assert status.name == "test-agent"
        assert status.type == "test"
        assert status.status == "active"
        assert status.last_activity == now
        assert status.messages_processed == 10
        assert status.errors == 1
        assert status.uptime_seconds == 3600.0


class TestAgentManager:
    """Test AgentManager class."""
    
    @pytest.fixture
    def agent_manager(self):
        """Create an agent manager instance."""
        return AgentManager()
    
    @pytest.mark.asyncio
    async def test_initialization(self, agent_manager):
        """Test agent manager initialization."""
        await agent_manager.initialize()
        
        assert agent_manager._running is True
        assert len(agent_manager.agent_configs) > 0
        assert len(agent_manager.agent_status) > 0
        
        # Check that default agents are configured
        assert "supply-chain" in agent_manager.agent_configs
        assert "threat-assessment" in agent_manager.agent_configs
        assert "resource-optimizer" in agent_manager.agent_configs
        assert "mission-coordinator" in agent_manager.agent_configs
    
    @pytest.mark.asyncio
    async def test_load_agent_configurations_with_files(self, agent_manager, tmp_path):
        """Test loading agent configurations from files."""
        # Create config directory and file
        config_dir = tmp_path / "config" / "agents"
        config_dir.mkdir(parents=True)
        
        config_file = config_dir / "custom-agent.json"
        config_data = {
            "name": "custom-agent",
            "type": "custom",
            "model": "gpt-3.5-turbo",
            "temperature": 0.8,
            "max_tokens": 1500,
            "system_prompt": "Custom prompt",
            "tools": ["custom_tool"],
            "enabled": True
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Mock Path to return our temp directory
        with patch('pathlib.Path') as mock_path:
            mock_path.return_value = config_dir.parent.parent
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.glob.return_value = [config_file]
            
            await agent_manager._load_agent_configurations()
        
        assert "custom-agent" in agent_manager.agent_configs
        config = agent_manager.agent_configs["custom-agent"]
        assert config.name == "custom-agent"
        assert config.type == "custom"
        assert config.model == "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_load_agent_configurations_invalid_file(self, agent_manager, tmp_path):
        """Test handling invalid configuration files."""
        config_dir = tmp_path / "config" / "agents"
        config_dir.mkdir(parents=True)
        
        config_file = config_dir / "invalid.json"
        with open(config_file, 'w') as f:
            f.write("invalid json")
        
        with patch('pathlib.Path') as mock_path:
            mock_path.return_value = config_dir.parent.parent
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.glob.return_value = [config_file]
            
            # Should not raise exception
            await agent_manager._load_agent_configurations()
    
    @pytest.mark.asyncio
    async def test_start_agent_success(self, agent_manager):
        """Test successfully starting an agent."""
        await agent_manager.initialize()
        
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            
            result = await agent_manager.start_agent("supply-chain")
            
            assert result is True
            assert "supply-chain" in agent_manager.agents
            assert agent_manager.agent_status["supply-chain"].status == "active"
            assert agent_manager.agent_status["supply-chain"].last_activity is not None
    
    @pytest.mark.asyncio
    async def test_start_agent_not_found(self, agent_manager):
        """Test starting a non-existent agent."""
        await agent_manager.initialize()
        
        result = await agent_manager.start_agent("non-existent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_start_agent_already_running(self, agent_manager):
        """Test starting an already running agent."""
        await agent_manager.initialize()
        
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            
            # Start agent first time
            await agent_manager.start_agent("supply-chain")
            
            # Try to start again
            result = await agent_manager.start_agent("supply-chain")
            
            assert result is True
            assert mock_create.call_count == 1  # Should only be called once
    
    @pytest.mark.asyncio
    async def test_start_agent_with_config_override(self, agent_manager):
        """Test starting an agent with configuration override."""
        await agent_manager.initialize()
        
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            
            override = {"temperature": 0.9}
            result = await agent_manager.start_agent("supply-chain", override)
            
            assert result is True
            # Check that config was updated
            call_args = mock_create.call_args[0][0]
            assert call_args.temperature == 0.9
    
    @pytest.mark.asyncio
    async def test_start_agent_creation_failure(self, agent_manager):
        """Test handling agent creation failure."""
        await agent_manager.initialize()
        
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_create.return_value = None
            
            result = await agent_manager.start_agent("supply-chain")
            
            assert result is False
            assert "supply-chain" not in agent_manager.agents
    
    @pytest.mark.asyncio
    async def test_start_agent_exception(self, agent_manager):
        """Test handling exception during agent start."""
        await agent_manager.initialize()
        
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_create.side_effect = Exception("Test error")
            
            result = await agent_manager.start_agent("supply-chain")
            
            assert result is False
            assert agent_manager.agent_status["supply-chain"].status == "error"
            assert agent_manager.agent_status["supply-chain"].errors == 1
    
    @pytest.mark.asyncio
    async def test_stop_agent_success(self, agent_manager):
        """Test successfully stopping an agent."""
        await agent_manager.initialize()
        
        # Start agent first
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            await agent_manager.start_agent("supply-chain")
        
        with patch.object(agent_manager, '_stop_agent_instance') as mock_stop:
            mock_stop.return_value = None
            
            result = await agent_manager.stop_agent("supply-chain")
            
            assert result is True
            assert "supply-chain" not in agent_manager.agents
            assert agent_manager.agent_status["supply-chain"].status == "inactive"
    
    @pytest.mark.asyncio
    async def test_stop_agent_not_running(self, agent_manager):
        """Test stopping a non-running agent."""
        await agent_manager.initialize()
        
        result = await agent_manager.stop_agent("supply-chain")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_stop_agent_exception(self, agent_manager):
        """Test handling exception during agent stop."""
        await agent_manager.initialize()
        
        # Start agent first
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            await agent_manager.start_agent("supply-chain")
        
        with patch.object(agent_manager, '_stop_agent_instance') as mock_stop:
            mock_stop.side_effect = Exception("Test error")
            
            result = await agent_manager.stop_agent("supply-chain")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_restart_agent(self, agent_manager):
        """Test restarting an agent."""
        await agent_manager.initialize()
        
        with patch.object(agent_manager, 'stop_agent') as mock_stop:
            mock_stop.return_value = True
            
            with patch.object(agent_manager, 'start_agent') as mock_start:
                mock_start.return_value = True
                
                result = await agent_manager.restart_agent("supply-chain")
                
                assert result is True
                mock_stop.assert_called_once_with("supply-chain")
                mock_start.assert_called_once_with("supply-chain")
    
    @pytest.mark.asyncio
    async def test_get_agent_status_single(self, agent_manager):
        """Test getting status for a single agent."""
        await agent_manager.initialize()
        
        status = await agent_manager.get_agent_status("supply-chain")
        
        assert "supply-chain" in status
        assert status["supply-chain"].name == "supply-chain"
        assert status["supply-chain"].status == "inactive"
    
    @pytest.mark.asyncio
    async def test_get_agent_status_all(self, agent_manager):
        """Test getting status for all agents."""
        await agent_manager.initialize()
        
        status = await agent_manager.get_agent_status()
        
        assert len(status) >= 4  # At least the default agents
        assert "supply-chain" in status
        assert "threat-assessment" in status
    
    @pytest.mark.asyncio
    async def test_get_agent_status_non_existent(self, agent_manager):
        """Test getting status for non-existent agent."""
        await agent_manager.initialize()
        
        status = await agent_manager.get_agent_status("non-existent")
        
        assert status == {}
    
    @pytest.mark.asyncio
    async def test_list_agents(self, agent_manager):
        """Test listing all agents."""
        await agent_manager.initialize()
        
        agents = await agent_manager.list_agents()
        
        assert len(agents) >= 4
        agent_names = [agent["name"] for agent in agents]
        assert "supply-chain" in agent_names
        assert "threat-assessment" in agent_names
        
        # Check agent structure
        agent = agents[0]
        assert "name" in agent
        assert "type" in agent
        assert "status" in agent
        assert "enabled" in agent
        assert "model" in agent
        assert "last_activity" in agent
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, agent_manager):
        """Test sending a message to an agent."""
        await agent_manager.initialize()
        
        # Start agent first
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            await agent_manager.start_agent("supply-chain")
        
        with patch.object(agent_manager, '_process_agent_message') as mock_process:
            mock_response = {"response": "Test response"}
            mock_process.return_value = mock_response
            
            result = await agent_manager.send_message("supply-chain", "Test message")
            
            assert result == mock_response
            assert agent_manager.agent_status["supply-chain"].messages_processed == 1
            assert agent_manager.agent_status["supply-chain"].last_activity is not None
    
    @pytest.mark.asyncio
    async def test_send_message_agent_not_running(self, agent_manager):
        """Test sending message to non-running agent."""
        await agent_manager.initialize()
        
        result = await agent_manager.send_message("supply-chain", "Test message")
        
        assert "error" in result
        assert "not running" in result["error"]
    
    @pytest.mark.asyncio
    async def test_send_message_exception(self, agent_manager):
        """Test handling exception during message processing."""
        await agent_manager.initialize()
        
        # Start agent first
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            await agent_manager.start_agent("supply-chain")
        
        with patch.object(agent_manager, '_process_agent_message') as mock_process:
            mock_process.side_effect = Exception("Test error")
            
            result = await agent_manager.send_message("supply-chain", "Test message")
            
            assert "error" in result
            assert agent_manager.agent_status["supply-chain"].errors == 1
    
    @pytest.mark.asyncio
    async def test_configure_agent_success(self, agent_manager):
        """Test configuring an agent."""
        await agent_manager.initialize()
        
        new_config = {
            "name": "supply-chain",
            "type": "supply-chain",
            "model": "gpt-3.5-turbo",
            "temperature": 0.9,
            "max_tokens": 1500,
            "system_prompt": "New prompt",
            "tools": ["new_tool"],
            "enabled": True
        }
        
        with patch.object(agent_manager, 'restart_agent') as mock_restart:
            mock_restart.return_value = True
            
            result = await agent_manager.configure_agent("supply-chain", new_config)
            
            assert result is True
            assert agent_manager.agent_configs["supply-chain"].model == "gpt-3.5-turbo"
            assert agent_manager.agent_configs["supply-chain"].temperature == 0.9
    
    @pytest.mark.asyncio
    async def test_configure_agent_not_found(self, agent_manager):
        """Test configuring non-existent agent."""
        await agent_manager.initialize()
        
        result = await agent_manager.configure_agent("non-existent", {})
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_configure_agent_exception(self, agent_manager):
        """Test handling exception during agent configuration."""
        await agent_manager.initialize()
        
        invalid_config = {"invalid": "config"}
        
        result = await agent_manager.configure_agent("supply-chain", invalid_config)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check(self, agent_manager):
        """Test health check functionality."""
        await agent_manager.initialize()
        
        # Start an agent and simulate activity
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            await agent_manager.start_agent("supply-chain")
        
        # Simulate some activity
        agent_manager.agent_status["supply-chain"].messages_processed = 10
        agent_manager.agent_status["supply-chain"].errors = 2
        
        health = await agent_manager.health_check()
        
        assert health["manager_status"] == "healthy"
        assert health["total_agents"] >= 4
        assert health["active_agents"] == 1
        assert "agent_health" in health
        assert "supply-chain" in health["agent_health"]
        
        agent_health = health["agent_health"]["supply-chain"]
        assert agent_health["messages_processed"] == 10
        assert agent_health["errors"] == 2
        assert agent_health["error_rate"] == 0.2
    
    @pytest.mark.asyncio
    async def test_shutdown(self, agent_manager):
        """Test shutting down the agent manager."""
        await agent_manager.initialize()
        
        # Start some agents
        with patch.object(agent_manager, '_create_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent
            await agent_manager.start_agent("supply-chain")
            await agent_manager.start_agent("threat-assessment")
        
        with patch.object(agent_manager, 'stop_agent') as mock_stop:
            mock_stop.return_value = True
            
            await agent_manager.shutdown()
            
            assert agent_manager._running is False
            assert mock_stop.call_count == 2  # Two agents stopped
    
    @pytest.mark.asyncio
    async def test_create_agent_supply_chain(self, agent_manager):
        """Test creating supply chain agent."""
        config = AgentConfig(
            name="test", 
            type="supply-chain",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="test prompt",
            enabled=True
        )
        
        with patch('open_logistics.application.agents.agent_manager.SupplyChainAgent') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            agent = await agent_manager._create_agent(config)
            
            assert agent == mock_instance
            mock_class.assert_called_once_with(config)
    
    @pytest.mark.asyncio
    async def test_create_agent_threat_assessment(self, agent_manager):
        """Test creating threat assessment agent."""
        config = AgentConfig(
            name="test", 
            type="threat-assessment",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="test prompt",
            enabled=True
        )
        
        with patch('open_logistics.application.agents.agent_manager.ThreatAssessmentAgent') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            agent = await agent_manager._create_agent(config)
            
            assert agent == mock_instance
            mock_class.assert_called_once_with(config)
    
    @pytest.mark.asyncio
    async def test_create_agent_resource_optimizer(self, agent_manager):
        """Test creating resource optimizer agent."""
        config = AgentConfig(
            name="test", 
            type="resource-optimizer",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="test prompt",
            enabled=True
        )
        
        with patch('open_logistics.application.agents.agent_manager.ResourceOptimizerAgent') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            agent = await agent_manager._create_agent(config)
            
            assert agent == mock_instance
            mock_class.assert_called_once_with(config)
    
    @pytest.mark.asyncio
    async def test_create_agent_mission_coordinator(self, agent_manager):
        """Test creating mission coordinator agent."""
        config = AgentConfig(
            name="test", 
            type="mission-coordinator",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="test prompt",
            enabled=True
        )
        
        with patch('open_logistics.application.agents.agent_manager.MissionCoordinatorAgent') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            agent = await agent_manager._create_agent(config)
            
            assert agent == mock_instance
            mock_class.assert_called_once_with(config)
    
    @pytest.mark.asyncio
    async def test_create_agent_unknown_type(self, agent_manager):
        """Test creating agent with unknown type."""
        config = AgentConfig(
            name="test", 
            type="unknown",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="test prompt",
            enabled=True
        )
        
        agent = await agent_manager._create_agent(config)
        
        assert agent is None
    
    @pytest.mark.asyncio
    async def test_create_agent_import_error(self, agent_manager):
        """Test handling import error during agent creation."""
        config = AgentConfig(
            name="test", 
            type="supply-chain",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="test prompt",
            enabled=True
        )
        
        with patch('open_logistics.application.agents.agent_manager.SupplyChainAgent') as mock_class:
            mock_class.side_effect = ImportError("Module not found")
            
            agent = await agent_manager._create_agent(config)
            
            assert agent is None
    
    @pytest.mark.asyncio
    async def test_stop_agent_instance_with_stop_method(self, agent_manager):
        """Test stopping agent instance with stop method."""
        mock_agent = Mock()
        mock_agent.stop = AsyncMock()
        
        await agent_manager._stop_agent_instance(mock_agent)
        
        mock_agent.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_agent_instance_without_stop_method(self, agent_manager):
        """Test stopping agent instance without stop method."""
        mock_agent = Mock()
        # No stop method
        
        # Should not raise exception
        await agent_manager._stop_agent_instance(mock_agent)
    
    @pytest.mark.asyncio
    async def test_process_agent_message_with_method(self, agent_manager):
        """Test processing agent message with process_message method."""
        mock_agent = Mock()
        mock_response = {"response": "Test response"}
        mock_agent.process_message = AsyncMock(return_value=mock_response)
        
        result = await agent_manager._process_agent_message(mock_agent, "test", {"context": "test"})
        
        assert result == mock_response
        mock_agent.process_message.assert_called_once_with("test", {"context": "test"})
    
    @pytest.mark.asyncio
    async def test_process_agent_message_without_method(self, agent_manager):
        """Test processing agent message without process_message method."""
        mock_agent = Mock()
        # No process_message method
        
        result = await agent_manager._process_agent_message(mock_agent, "test", None)
        
        assert "error" in result
        assert "does not support message processing" in result["error"] 