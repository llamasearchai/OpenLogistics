"""
Comprehensive tests for Threat Assessment Agent.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from open_logistics.application.agents.threat_assessment_agent import ThreatAssessmentAgent
from open_logistics.application.agents.agent_manager import AgentConfig


class TestThreatAssessmentAgent:
    """Test ThreatAssessmentAgent class."""
    
    @pytest.fixture
    def agent_config(self):
        """Create an agent configuration."""
        return AgentConfig(
            name="test-threat-assessment",
            type="threat-assessment",
            model="gpt-4",
            temperature=0.2,
            max_tokens=2000,
            system_prompt="Test threat assessment prompt",
            tools=["threat_analyzer", "risk_assessor"],
            enabled=True
        )
    
    @pytest.fixture
    def threat_agent(self, agent_config):
        """Create a threat assessment agent instance."""
        return ThreatAssessmentAgent(agent_config)
    
    def test_initialization(self, threat_agent, agent_config):
        """Test agent initialization."""
        assert threat_agent.config == agent_config
        assert threat_agent.running is False
        assert threat_agent.conversation_history == []
    
    @pytest.mark.asyncio
    async def test_start_agent(self, threat_agent):
        """Test starting the agent."""
        await threat_agent.start()
        
        assert threat_agent.running is True
    
    @pytest.mark.asyncio
    async def test_stop_agent(self, threat_agent):
        """Test stopping the agent."""
        await threat_agent.start()
        await threat_agent.stop()
        
        assert threat_agent.running is False
    
    @pytest.mark.asyncio
    async def test_process_message_not_running(self, threat_agent):
        """Test processing message when agent is not running."""
        result = await threat_agent.process_message("test message")
        
        assert "error" in result
        assert "not running" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, threat_agent):
        """Test successfully processing a message."""
        await threat_agent.start()
        
        result = await threat_agent.process_message("security threat analysis")
        
        assert result["response"] == "Threat assessment analysis: security threat analysis"
        assert result["agent_name"] == "test-threat-assessment"
        assert result["agent_type"] == "threat-assessment"
        assert result["risk_level"] == "medium"
        assert "recommendations" in result
        assert "timestamp" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_process_message_with_context(self, threat_agent):
        """Test processing message with context."""
        await threat_agent.start()
        
        context = {"security_level": "high", "location": "datacenter"}
        result = await threat_agent.process_message("analyze threats", context)
        
        assert result["response"] == "Threat assessment analysis: analyze threats"
        assert result["agent_name"] == "test-threat-assessment"
        assert result["agent_type"] == "threat-assessment"
        assert result["risk_level"] == "medium"
        assert "recommendations" in result
        assert "timestamp" in result 