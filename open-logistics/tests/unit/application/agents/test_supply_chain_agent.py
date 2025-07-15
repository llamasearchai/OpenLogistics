"""
Comprehensive tests for Supply Chain Agent.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from open_logistics.application.agents.supply_chain_agent import SupplyChainAgent
from open_logistics.application.agents.agent_manager import AgentConfig


class TestSupplyChainAgent:
    """Test SupplyChainAgent class."""
    
    @pytest.fixture
    def agent_config(self):
        """Create an agent configuration."""
        return AgentConfig(
            name="test-supply-chain",
            type="supply-chain",
            model="gpt-4",
            temperature=0.3,
            max_tokens=2000,
            system_prompt="Test system prompt",
            tools=["supply_chain_optimizer", "inventory_analyzer"],
            enabled=True
        )
    
    @pytest.fixture
    def supply_chain_agent(self, agent_config):
        """Create a supply chain agent instance."""
        return SupplyChainAgent(agent_config)
    
    def test_initialization(self, supply_chain_agent, agent_config):
        """Test agent initialization."""
        assert supply_chain_agent.config == agent_config
        assert supply_chain_agent.running is False
        assert supply_chain_agent.conversation_history == []
        assert supply_chain_agent.system_message["role"] == "system"
        assert supply_chain_agent.system_message["content"] == "Test system prompt"
    
    def test_initialization_with_default_prompt(self):
        """Test agent initialization with default system prompt."""
        config = AgentConfig(
            name="test",
            type="supply-chain",
            model="gpt-4",
            temperature=0.3,
            max_tokens=2000,
            system_prompt="",
            enabled=True
        )
        agent = SupplyChainAgent(config)
        
        assert "expert supply chain optimization agent" in agent.system_message["content"].lower()
        assert "supply chain analysis" in agent.system_message["content"].lower()
    
    def test_get_default_system_prompt(self, supply_chain_agent):
        """Test getting default system prompt."""
        prompt = supply_chain_agent._get_default_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "supply chain optimization" in prompt.lower()
        assert "inventory management" in prompt.lower()
        assert "demand prediction" in prompt.lower()
        assert "risk assessment" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_start_agent(self, supply_chain_agent):
        """Test starting the agent."""
        await supply_chain_agent.start()
        
        assert supply_chain_agent.running is True
    
    @pytest.mark.asyncio
    async def test_stop_agent(self, supply_chain_agent):
        """Test stopping the agent."""
        await supply_chain_agent.start()
        await supply_chain_agent.stop()
        
        assert supply_chain_agent.running is False
    
    @pytest.mark.asyncio
    async def test_process_message_not_running(self, supply_chain_agent):
        """Test processing message when agent is not running."""
        result = await supply_chain_agent.process_message("test message")
        
        assert "error" in result
        assert "not running" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, supply_chain_agent):
        """Test successfully processing a message."""
        await supply_chain_agent.start()
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.process_message("test message")
            
            assert result["response"] == "Test response"
            assert result["agent_name"] == "test-supply-chain"
            assert result["agent_type"] == "supply-chain"
            assert result["model"] == "gpt-4"
            assert result["tokens_used"] == 100
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_process_message_with_context(self, supply_chain_agent):
        """Test processing message with context."""
        await supply_chain_agent.start()
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        context = {"inventory": {"item1": 100, "item2": 50}}
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.process_message("test message", context)
            
            assert result["response"] == "Test response"
            # Check that context was included in the API call
            call_args = mock_create.call_args[1]
            messages = call_args["messages"]
            assert len(messages) == 3  # system + context + user message
            assert "Context:" in messages[1]["content"]
    
    @pytest.mark.asyncio
    async def test_process_message_no_usage(self, supply_chain_agent):
        """Test processing message when response has no usage info."""
        await supply_chain_agent.start()
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = None
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.process_message("test message")
            
            assert result["tokens_used"] == 0
    
    @pytest.mark.asyncio
    async def test_process_message_exception(self, supply_chain_agent):
        """Test handling exception during message processing."""
        await supply_chain_agent.start()
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("API error")
            
            result = await supply_chain_agent.process_message("test message")
            
            assert "error" in result
            assert "API error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_conversation_history_tracking(self, supply_chain_agent):
        """Test that conversation history is tracked."""
        await supply_chain_agent.start()
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            await supply_chain_agent.process_message("test message", {"test": "context"})
            
            assert len(supply_chain_agent.conversation_history) == 1
            history_entry = supply_chain_agent.conversation_history[0]
            assert history_entry["user_message"] == "test message"
            assert history_entry["context"] == {"test": "context"}
            assert history_entry["assistant_response"] == "Test response"
            assert history_entry["model"] == "gpt-4"
            assert history_entry["tokens_used"] == 100
            assert "timestamp" in history_entry
    
    @pytest.mark.asyncio
    async def test_analyze_supply_chain(self, supply_chain_agent):
        """Test supply chain analysis."""
        await supply_chain_agent.start()
        
        supply_chain_data = {
            "suppliers": ["Supplier A", "Supplier B"],
            "inventory": {"item1": 100, "item2": 50},
            "demand": {"item1": 80, "item2": 60}
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Analysis complete"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 150
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.analyze_supply_chain(supply_chain_data)
            
            assert result["response"] == "Analysis complete"
            
            # Check that the analysis prompt was properly formatted
            call_args = mock_create.call_args[1]
            messages = call_args["messages"]
            user_message = messages[-1]["content"]
            assert "Supply Chain Data:" in user_message
            assert "optimization recommendations" in user_message
            assert json.dumps(supply_chain_data, indent=2) in user_message
    
    @pytest.mark.asyncio
    async def test_optimize_inventory(self, supply_chain_agent):
        """Test inventory optimization."""
        await supply_chain_agent.start()
        
        inventory_data = {
            "current_stock": {"item1": 100, "item2": 50},
            "reorder_points": {"item1": 20, "item2": 15},
            "demand_history": {"item1": [80, 85, 90], "item2": [55, 60, 65]}
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Optimization complete"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 200
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.optimize_inventory(inventory_data)
            
            assert result["response"] == "Optimization complete"
            
            # Check that the optimization prompt was properly formatted
            call_args = mock_create.call_args[1]
            messages = call_args["messages"]
            user_message = messages[-1]["content"]
            assert "Inventory Data:" in user_message
            assert "Optimal inventory levels" in user_message
            assert json.dumps(inventory_data, indent=2) in user_message
    
    @pytest.mark.asyncio
    async def test_forecast_demand(self, supply_chain_agent):
        """Test demand forecasting."""
        await supply_chain_agent.start()
        
        historical_data = {
            "sales_history": [100, 110, 120, 130, 140],
            "seasonal_factors": {"Q1": 0.9, "Q2": 1.1, "Q3": 1.2, "Q4": 0.8},
            "external_factors": {"economic_index": 1.05}
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Forecast complete"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 180
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.forecast_demand(historical_data, 45)
            
            assert result["response"] == "Forecast complete"
            
            # Check that the forecast prompt was properly formatted
            call_args = mock_create.call_args[1]
            messages = call_args["messages"]
            user_message = messages[-1]["content"]
            assert "Historical Data:" in user_message
            assert "Forecast Horizon: 45 days" in user_message
            assert "next 45 days" in user_message
            assert json.dumps(historical_data, indent=2) in user_message
    
    @pytest.mark.asyncio
    async def test_forecast_demand_default_horizon(self, supply_chain_agent):
        """Test demand forecasting with default horizon."""
        await supply_chain_agent.start()
        
        historical_data = {"sales": [100, 110, 120]}
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Forecast complete"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 180
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.forecast_demand(historical_data)
            
            # Check that default 30-day horizon was used
            call_args = mock_create.call_args[1]
            messages = call_args["messages"]
            user_message = messages[-1]["content"]
            assert "Forecast Horizon: 30 days" in user_message
            assert "next 30 days" in user_message
    
    @pytest.mark.asyncio
    async def test_assess_supply_risk(self, supply_chain_agent):
        """Test supply risk assessment."""
        await supply_chain_agent.start()
        
        supply_data = {
            "suppliers": {
                "Supplier A": {"reliability": 0.95, "location": "USA"},
                "Supplier B": {"reliability": 0.88, "location": "China"}
            },
            "lead_times": {"Supplier A": 5, "Supplier B": 15},
            "geopolitical_risks": {"China": "medium", "USA": "low"}
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Risk assessment complete"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 220
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.assess_supply_risk(supply_data)
            
            assert result["response"] == "Risk assessment complete"
            
            # Check that the risk assessment prompt was properly formatted
            call_args = mock_create.call_args[1]
            messages = call_args["messages"]
            user_message = messages[-1]["content"]
            assert "Supply Data:" in user_message
            assert "risk factors" in user_message
            assert "mitigation strategies" in user_message
            assert json.dumps(supply_data, indent=2) in user_message
    
    @pytest.mark.asyncio
    async def test_optimize_routes(self, supply_chain_agent):
        """Test route optimization."""
        await supply_chain_agent.start()
        
        route_data = {
            "destinations": ["City A", "City B", "City C"],
            "distances": {"A-B": 100, "B-C": 150, "A-C": 200},
            "vehicle_capacity": 1000,
            "delivery_windows": {"City A": "9-12", "City B": "10-14", "City C": "13-17"}
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Route optimization complete"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 250
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await supply_chain_agent.optimize_routes(route_data)
            
            assert result["response"] == "Route optimization complete"
            
            # Check that the route optimization prompt was properly formatted
            call_args = mock_create.call_args[1]
            messages = call_args["messages"]
            user_message = messages[-1]["content"]
            assert "Route Data:" in user_message
            assert "efficient routes" in user_message
            assert "transportation cost reduction" in user_message
            assert json.dumps(route_data, indent=2) in user_message
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, supply_chain_agent):
        """Test getting conversation history."""
        await supply_chain_agent.start()
        
        # Add some history
        supply_chain_agent.conversation_history = [
            {"timestamp": "2024-01-01", "user_message": "test1", "assistant_response": "response1"},
            {"timestamp": "2024-01-02", "user_message": "test2", "assistant_response": "response2"}
        ]
        
        history = await supply_chain_agent.get_conversation_history()
        
        assert len(history) == 2
        assert history[0]["user_message"] == "test1"
        assert history[1]["user_message"] == "test2"
        
        # Ensure it's a copy, not the original
        history.append({"new": "entry"})
        assert len(supply_chain_agent.conversation_history) == 2
    
    @pytest.mark.asyncio
    async def test_clear_conversation_history(self, supply_chain_agent):
        """Test clearing conversation history."""
        await supply_chain_agent.start()
        
        # Add some history
        supply_chain_agent.conversation_history = [
            {"timestamp": "2024-01-01", "user_message": "test1", "assistant_response": "response1"}
        ]
        
        await supply_chain_agent.clear_conversation_history()
        
        assert len(supply_chain_agent.conversation_history) == 0
    
    @pytest.mark.asyncio
    async def test_message_api_parameters(self, supply_chain_agent):
        """Test that API calls use correct parameters from config."""
        await supply_chain_agent.start()
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        with patch.object(supply_chain_agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            await supply_chain_agent.process_message("test message")
            
            # Check API call parameters
            call_args = mock_create.call_args[1]
            assert call_args["model"] == "gpt-4"
            assert call_args["temperature"] == 0.3
            assert call_args["max_tokens"] == 2000
            assert len(call_args["messages"]) == 2  # system + user message
            
            # Check message structure
            messages = call_args["messages"]
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "Test system prompt"
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "test message" 