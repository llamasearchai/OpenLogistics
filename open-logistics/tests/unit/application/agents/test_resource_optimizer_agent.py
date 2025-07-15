"""
Comprehensive tests for Resource Optimizer Agent.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from open_logistics.application.agents.resource_optimizer_agent import ResourceOptimizerAgent
from open_logistics.application.agents.agent_manager import AgentConfig


class TestResourceOptimizerAgent:
    """Test ResourceOptimizerAgent class."""
    
    @pytest.fixture
    def agent_config(self):
        """Create an agent configuration."""
        return AgentConfig(
            name="test-resource-optimizer",
            type="resource-optimizer",
            model="gpt-4",
            temperature=0.4,
            max_tokens=2000,
            system_prompt="Test resource optimizer prompt",
            tools=["resource_allocator", "capacity_planner"],
            enabled=True
        )
    
    @pytest.fixture
    def resource_agent(self, agent_config):
        """Create a resource optimizer agent instance."""
        return ResourceOptimizerAgent(agent_config)
    
    def test_initialization(self, resource_agent, agent_config):
        """Test agent initialization."""
        assert resource_agent.config == agent_config
        assert resource_agent.running is False
        assert resource_agent.conversation_history == []
    
    @pytest.mark.asyncio
    async def test_start_agent(self, resource_agent):
        """Test starting the agent."""
        await resource_agent.start()
        
        assert resource_agent.running is True
    
    @pytest.mark.asyncio
    async def test_stop_agent(self, resource_agent):
        """Test stopping the agent."""
        await resource_agent.start()
        await resource_agent.stop()
        
        assert resource_agent.running is False
    
    @pytest.mark.asyncio
    async def test_process_message_not_running(self, resource_agent):
        """Test processing message when agent is not running."""
        result = await resource_agent.process_message("test message")
        
        assert "error" in result
        assert "not running" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, resource_agent):
        """Test successfully processing a message."""
        await resource_agent.start()
        
        result = await resource_agent.process_message("optimize resource allocation")
        
        assert result["response"] == "Resource optimization analysis: optimize resource allocation"
        assert result["agent_name"] == "test-resource-optimizer"
        assert result["agent_type"] == "resource-optimizer"
        assert result["optimization_score"] == 0.85
        assert "recommendations" in result
        assert "timestamp" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_process_message_with_context(self, resource_agent):
        """Test processing message with context."""
        await resource_agent.start()
        
        context = {"current_utilization": 0.75, "capacity": 1000}
        result = await resource_agent.process_message("analyze resources", context)
        
        assert result["response"] == "Resource optimization analysis: analyze resources"
        assert result["agent_name"] == "test-resource-optimizer"
        assert result["agent_type"] == "resource-optimizer"
        assert result["optimization_score"] == 0.85
        assert "recommendations" in result
        assert "timestamp" in result 