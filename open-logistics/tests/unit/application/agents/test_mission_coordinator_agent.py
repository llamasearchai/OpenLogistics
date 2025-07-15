"""
Comprehensive tests for Mission Coordinator Agent.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from open_logistics.application.agents.mission_coordinator_agent import MissionCoordinatorAgent
from open_logistics.application.agents.agent_manager import AgentConfig


class TestMissionCoordinatorAgent:
    """Test MissionCoordinatorAgent class."""
    
    @pytest.fixture
    def agent_config(self):
        """Create an agent configuration."""
        return AgentConfig(
            name="test-mission-coordinator",
            type="mission-coordinator",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
            system_prompt="Test mission coordinator prompt",
            tools=["mission_planner", "task_coordinator"],
            enabled=True
        )
    
    @pytest.fixture
    def mission_agent(self, agent_config):
        """Create a mission coordinator agent instance."""
        return MissionCoordinatorAgent(agent_config)
    
    def test_initialization(self, mission_agent, agent_config):
        """Test agent initialization."""
        assert mission_agent.config == agent_config
        assert mission_agent.running is False
        assert mission_agent.conversation_history == []
    
    @pytest.mark.asyncio
    async def test_start_agent(self, mission_agent):
        """Test starting the agent."""
        await mission_agent.start()
        
        assert mission_agent.running is True
    
    @pytest.mark.asyncio
    async def test_stop_agent(self, mission_agent):
        """Test stopping the agent."""
        await mission_agent.start()
        await mission_agent.stop()
        
        assert mission_agent.running is False
    
    @pytest.mark.asyncio
    async def test_process_message_not_running(self, mission_agent):
        """Test processing message when agent is not running."""
        result = await mission_agent.process_message("test message")
        
        assert "error" in result
        assert "not running" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, mission_agent):
        """Test successfully processing a message."""
        await mission_agent.start()
        
        result = await mission_agent.process_message("coordinate mission tasks")
        
        assert result["response"] == "Mission coordination analysis: coordinate mission tasks"
        assert result["agent_name"] == "test-mission-coordinator"
        assert result["agent_type"] == "mission-coordinator"
        assert result["mission_status"] == "in_progress"
        assert "recommendations" in result
        assert "timestamp" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_process_message_with_context(self, mission_agent):
        """Test processing message with context."""
        await mission_agent.start()
        
        context = {"mission_type": "logistics", "priority": "high"}
        result = await mission_agent.process_message("coordinate tasks", context)
        
        assert result["response"] == "Mission coordination analysis: coordinate tasks"
        assert result["agent_name"] == "test-mission-coordinator"
        assert result["agent_type"] == "mission-coordinator"
        assert result["mission_status"] == "in_progress"
        assert "recommendations" in result
        assert "timestamp" in result 