"""
Unit tests for CLI commands coverage.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from typer.testing import CliRunner
import json
from pathlib import Path

from open_logistics.presentation.cli.main import (
    app,
    _load_optimization_config,
    _load_supply_chain_data,
    _run_optimization,
    _run_predictions,
    _display_optimization_results,
    _display_prediction_results,
    _list_agents,
    _start_agent,
    _stop_agent,
    _show_agent_status,
    _configure_agent,
    _setup_database,
    _setup_mlx,
    _setup_monitoring,
    _save_results,
)


class TestCLICommandsCoverage:
    """Additional tests for CLI commands to improve coverage."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    def test_version_command_detailed(self):
        """Test version command with detailed output."""
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Open Logistics Platform" in result.stdout
        assert "1.0.2" in result.stdout

    def test_predict_non_demand(self):
        """Test predict command with non-demand type."""
        with patch('open_logistics.application.use_cases.predict_demand.PredictDemandUseCase') as mock_use_case:
            mock_instance = mock_use_case.return_value
            mock_instance.execute = AsyncMock(return_value={
                "predictions": {"period_1": 150.0},
                "confidence_scores": {"period_1": 0.80},
                "type": "supply",
                "time_horizon": 1
            })

            result = self.runner.invoke(app, [
                "predict",
                "--type", "supply",
                "--horizon", "1"
            ])
            
            assert result.exit_code == 0

    def test_agents_list_command_detailed(self):
        """Test agents list command with detailed output."""
        result = self.runner.invoke(app, ["agents", "list"])
        assert result.exit_code == 0
        assert "AI Agents" in result.stdout

    def test_serve_command(self):
        """Test serve command."""
        with patch('uvicorn.run') as mock_run:
            result = self.runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "8080"])
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_serve_command_with_reload(self):
        """Test serve command with reload."""
        with patch('uvicorn.run') as mock_run:
            result = self.runner.invoke(app, ["serve", "--reload"])
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_optimize_command_basic(self):
        """Test optimize command with basic parameters."""
        with patch('open_logistics.application.use_cases.optimize_supply_chain.OptimizeSupplyChainUseCase') as mock_use_case:
            mock_instance = mock_use_case.return_value
            mock_result = Mock()
            mock_result.optimized_plan = {"inventory": {"item1": 100}}
            mock_result.confidence_score = 0.85
            mock_result.execution_time_ms = 150.0
            mock_result.resource_utilization = {"cpu": 0.6}
            mock_instance.execute = AsyncMock(return_value=mock_result)

            result = self.runner.invoke(app, ["optimize"])
            assert result.exit_code == 0

    def test_optimize_command_with_config(self, tmp_path):
        """Test optimize command with config file."""
        config_file = tmp_path / "config.json"
        config_data = {"constraints": {"budget": 500000}}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        with patch('open_logistics.application.use_cases.optimize_supply_chain.OptimizeSupplyChainUseCase') as mock_use_case:
            mock_instance = mock_use_case.return_value
            mock_result = Mock()
            mock_result.optimized_plan = {"inventory": {"item1": 100}}
            mock_result.confidence_score = 0.85
            mock_result.execution_time_ms = 150.0
            mock_result.resource_utilization = {"cpu": 0.6}
            mock_instance.execute = AsyncMock(return_value=mock_result)

            result = self.runner.invoke(app, ["optimize", "--config", str(config_file)])
            assert result.exit_code == 0

    def test_optimize_command_with_data_file(self, tmp_path):
        """Test optimize command with data file."""
        data_file = tmp_path / "data.json"
        data = {"inventory": {"item1": 100, "item2": 200}}
        
        with open(data_file, 'w') as f:
            json.dump(data, f)

        with patch('open_logistics.application.use_cases.optimize_supply_chain.OptimizeSupplyChainUseCase') as mock_use_case:
            mock_instance = mock_use_case.return_value
            mock_result = Mock()
            mock_result.optimized_plan = {"inventory": {"item1": 100}}
            mock_result.confidence_score = 0.85
            mock_result.execution_time_ms = 150.0
            mock_result.resource_utilization = {"cpu": 0.6}
            mock_instance.execute = AsyncMock(return_value=mock_result)

            result = self.runner.invoke(app, ["optimize", "--data", str(data_file)])
            assert result.exit_code == 0

    def test_optimize_command_json_output(self):
        """Test optimize command with JSON output."""
        with patch('open_logistics.application.use_cases.optimize_supply_chain.OptimizeSupplyChainUseCase') as mock_use_case:
            mock_instance = mock_use_case.return_value
            mock_result = Mock()
            mock_result.optimized_plan = {"inventory": {"item1": 100}}
            mock_result.confidence_score = 0.85
            mock_result.execution_time_ms = 150.0
            mock_result.resource_utilization = {"cpu": 0.6}
            mock_instance.execute = AsyncMock(return_value=mock_result)

            result = self.runner.invoke(app, ["optimize", "--format", "json"])
            assert result.exit_code == 0

    def test_optimize_command_with_save(self, tmp_path):
        """Test optimize command with save results."""
        save_file = tmp_path / "results.json"

        with patch('open_logistics.application.use_cases.optimize_supply_chain.OptimizeSupplyChainUseCase') as mock_use_case:
            mock_instance = mock_use_case.return_value
            mock_result = Mock()
            mock_result.optimized_plan = {"inventory": {"item1": 100}}
            mock_result.confidence_score = 0.85
            mock_result.execution_time_ms = 150.0
            mock_result.resource_utilization = {"cpu": 0.6}
            mock_instance.execute = AsyncMock(return_value=mock_result)

            result = self.runner.invoke(app, ["optimize", "--save", str(save_file)])
            assert result.exit_code == 0
            assert save_file.exists()

    def test_optimize_command_failure(self):
        """Test optimize command failure."""
        with patch('open_logistics.application.use_cases.optimize_supply_chain.OptimizeSupplyChainUseCase') as mock_use_case:
            mock_use_case.side_effect = Exception("Optimization failed")

            result = self.runner.invoke(app, ["optimize"])
            assert result.exit_code == 1

    def test_predict_command_threats(self):
        """Test predict command with threats type."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.start_agent = AsyncMock()
            mock_manager.send_message = AsyncMock(return_value={
                "response": "Threat analysis complete",
                "agent_name": "threat-assessment"
            })
            mock_manager.shutdown = AsyncMock()

            result = self.runner.invoke(app, ["predict", "--type", "threats"])
            assert result.exit_code == 0

    def test_predict_command_failures(self):
        """Test predict command with failures type."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.start_agent = AsyncMock()
            mock_manager.send_message = AsyncMock(return_value={
                "response": "Failure analysis complete",
                "agent_name": "resource-optimizer"
            })
            mock_manager.shutdown = AsyncMock()

            result = self.runner.invoke(app, ["predict", "--type", "failures"])
            assert result.exit_code == 0

    def test_predict_command_capacity(self):
        """Test predict command with capacity type."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.start_agent = AsyncMock()
            mock_manager.send_message = AsyncMock(return_value={
                "response": "Capacity analysis complete",
                "agent_name": "resource-optimizer"
            })
            mock_manager.shutdown = AsyncMock()

            result = self.runner.invoke(app, ["predict", "--type", "capacity"])
            assert result.exit_code == 0

    def test_predict_command_json_output(self):
        """Test predict command with JSON output."""
        with patch('open_logistics.application.use_cases.predict_demand.PredictDemandUseCase') as mock_use_case:
            mock_instance = mock_use_case.return_value
            mock_instance.execute = AsyncMock(return_value={
                "predictions": {"day_1": 100, "day_2": 110},
                "confidence_scores": {"day_1": 0.85, "day_2": 0.82},
                "type": "demand"
            })

            result = self.runner.invoke(app, ["predict", "--format", "json"])
            assert result.exit_code == 0

    def test_predict_command_failure(self):
        """Test predict command failure."""
        with patch('open_logistics.application.use_cases.predict_demand.PredictDemandUseCase') as mock_use_case:
            mock_use_case.side_effect = Exception("Prediction failed")

            result = self.runner.invoke(app, ["predict"])
            assert result.exit_code == 1

    def test_agents_start_command(self):
        """Test agents start command."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.start_agent = AsyncMock(return_value=True)
            mock_manager.get_agent_status = AsyncMock(return_value={
                "supply-chain": Mock(status="active", type="supply-chain", last_activity=None)
            })

            result = self.runner.invoke(app, ["agents", "start", "--type", "supply-chain"])
            assert result.exit_code == 0

    def test_agents_stop_command(self):
        """Test agents stop command."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.stop_agent = AsyncMock(return_value=True)

            result = self.runner.invoke(app, ["agents", "stop", "--type", "supply-chain"])
            assert result.exit_code == 0

    def test_agents_status_command(self):
        """Test agents status command."""
        with patch('open_logistics.presentation.cli.main.asyncio.run') as mock_run:
            result = self.runner.invoke(app, ["agents", "status"])
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_agents_configure_command(self, tmp_path):
        """Test agents configure command."""
        config_file = tmp_path / "config.json"
        config_data = {"temperature": 0.5}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        with patch('open_logistics.presentation.cli.main.asyncio.run') as mock_run:
            result = self.runner.invoke(app, ["agents", "configure", "--type", "supply-chain", "--config", str(config_file)])
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_agents_unknown_action(self):
        """Test agents command with unknown action."""
        result = self.runner.invoke(app, ["agents", "unknown"])
        assert result.exit_code == 1

    def test_agents_command_failure(self):
        """Test agents command failure."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_agent_manager.side_effect = Exception("Agent error")

            result = self.runner.invoke(app, ["agents", "start", "--type", "supply-chain"])
            assert result.exit_code == 1

    def test_setup_command_basic(self):
        """Test setup command with basic parameters."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            result = self.runner.invoke(app, ["setup"])
            assert result.exit_code == 0

    def test_setup_command_production(self):
        """Test setup command for production environment."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            result = self.runner.invoke(app, ["setup", "--env", "production"])
            assert result.exit_code == 0

    def test_setup_command_no_database(self):
        """Test setup command without database."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            result = self.runner.invoke(app, ["setup", "--no-database"])
            assert result.exit_code == 0

    def test_setup_command_no_mlx(self):
        """Test setup command without MLX."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            result = self.runner.invoke(app, ["setup", "--no-mlx"])
            assert result.exit_code == 0

    def test_setup_command_no_monitoring(self):
        """Test setup command without monitoring."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            result = self.runner.invoke(app, ["setup", "--no-monitoring"])
            assert result.exit_code == 0

    def test_setup_command_failure(self):
        """Test setup command failure."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = Exception("Setup failed")

            result = self.runner.invoke(app, ["setup"])
            assert result.exit_code == 1


class TestCLIHelperFunctions:
    """Test CLI helper functions."""
    
    def test_load_optimization_config_file_exists(self, tmp_path):
        """Test loading optimization config from file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "constraints": {"budget": 500000},
            "weights": {"cost": 0.5, "efficiency": 0.5}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        result = _load_optimization_config(config_file)
        
        assert result == config_data
    
    def test_load_optimization_config_file_not_exists(self):
        """Test loading optimization config when file doesn't exist."""
        result = _load_optimization_config(Path("nonexistent.json"))
        
        assert "constraints" in result
        assert "weights" in result
        assert "thresholds" in result
    
    def test_load_optimization_config_none(self):
        """Test loading optimization config with None input."""
        result = _load_optimization_config(None)
        
        assert "constraints" in result
        assert "weights" in result
        assert "thresholds" in result
    
    def test_load_supply_chain_data_file_exists(self, tmp_path):
        """Test loading supply chain data from file."""
        data_file = tmp_path / "data.json"
        data = {
            "inventory": {"item1": 100, "item2": 200},
            "demand_history": [10, 20, 30]
        }
        
        with open(data_file, 'w') as f:
            json.dump(data, f)
        
        result = _load_supply_chain_data(data_file)
        
        assert result == data
    
    def test_load_supply_chain_data_file_not_exists(self):
        """Test loading supply chain data when file doesn't exist."""
        result = _load_supply_chain_data(Path("nonexistent.json"))
        
        assert "inventory" in result
        assert "demand_history" in result
        assert "constraints" in result
        assert "locations" in result
    
    def test_load_supply_chain_data_none(self):
        """Test loading supply chain data with None input."""
        result = _load_supply_chain_data(None)
        
        assert "inventory" in result
        assert "demand_history" in result
        assert "constraints" in result
        assert "locations" in result
    
    @pytest.mark.asyncio
    async def test_run_optimization(self):
        """Test running optimization."""
        chain_data = {"inventory": {"item1": 100}}
        config = {"constraints": {"budget": 1000}}
        objectives = ["minimize_cost"]
        time_horizon = 30
        priority = "high"
        
        with patch('open_logistics.presentation.cli.main.OptimizeSupplyChainUseCase') as mock_use_case:
            mock_instance = Mock()
            mock_use_case.return_value = mock_instance
            
            mock_result = Mock()
            mock_result.optimized_plan = {"plan": "test"}
            mock_result.confidence_score = 0.85
            mock_result.execution_time_ms = 100.0
            mock_result.resource_utilization = {"cpu": 0.5}
            
            mock_instance.execute = AsyncMock(return_value=mock_result)
            
            result = await _run_optimization(chain_data, config, objectives, time_horizon, priority)
            
            assert result["optimized_plan"] == {"plan": "test"}
            assert result["confidence_score"] == 0.85
            assert result["execution_time_ms"] == 100.0
            assert result["resource_utilization"] == {"cpu": 0.5}
    
    @pytest.mark.asyncio
    async def test_run_predictions_demand(self):
        """Test running demand predictions."""
        with patch('open_logistics.presentation.cli.main.PredictDemandUseCase') as mock_use_case:
            mock_instance = Mock()
            mock_use_case.return_value = mock_instance
            
            mock_result = {"predictions": {"day_1": 100, "day_2": 110}}
            mock_instance.execute = AsyncMock(return_value=mock_result)
            
            result = await _run_predictions("historical", "demand", 7, 0.8)
            
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_run_predictions_threats(self):
        """Test running threat predictions."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.start_agent = AsyncMock()
            mock_manager.send_message = AsyncMock(return_value={
                "response": "Threat analysis complete",
                "agent_name": "threat-assessment"
            })
            mock_manager.shutdown = AsyncMock()
            
            result = await _run_predictions("real-time", "threats", 5, 0.9)
            
            assert "predictions" in result
            assert "confidence_scores" in result
            assert result["type"] == "threats"
            assert result["time_horizon"] == 5
            assert "agent_response" in result
    
    def test_display_optimization_results_json(self):
        """Test displaying optimization results in JSON format."""
        result = {
            "optimized_plan": {"inventory": {"item1": 100}},
            "confidence_score": 0.85,
            "execution_time_ms": 150.0,
            "resource_utilization": {"cpu": 0.6}
        }
        
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            _display_optimization_results(result, "json")
            
            mock_console.print.assert_called()
    
    def test_display_optimization_results_table(self):
        """Test displaying optimization results in table format."""
        result = {
            "optimized_plan": {"inventory": {"item1": 100}},
            "confidence_score": 0.85,
            "execution_time_ms": 150.0,
            "resource_utilization": {"cpu": 0.6}
        }
        
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            _display_optimization_results(result, "table")
            
            assert mock_console.print.call_count >= 2
    
    def test_display_prediction_results_json(self):
        """Test displaying prediction results in JSON format."""
        predictions = {
            "predictions": {"day_1": 100, "day_2": 110},
            "confidence_scores": {"day_1": 0.85, "day_2": 0.82},
            "type": "demand"
        }
        
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            _display_prediction_results(predictions, "json")
            
            mock_console.print.assert_called()
    
    def test_display_prediction_results_table(self):
        """Test displaying prediction results in table format."""
        predictions = {
            "predictions": {"day_1": 100, "day_2": 110},
            "confidence_scores": {"day_1": 0.85, "day_2": 0.82},
            "type": "demand"
        }
        
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            _display_prediction_results(predictions, "table")
            
            mock_console.print.assert_called()
    
    def test_list_agents(self):
        """Test listing agents."""
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            _list_agents()
            
            mock_console.print.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_agent_success(self):
        """Test successfully starting an agent."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.start_agent = AsyncMock(return_value=True)
            mock_manager.get_agent_status = AsyncMock(return_value={
                "supply-chain": Mock(status="active", type="supply-chain", last_activity=None)
            })
            
            with patch('open_logistics.presentation.cli.main.console') as mock_console:
                await _start_agent("supply-chain", None)
                
                mock_console.print.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_agent_no_type(self):
        """Test starting agent without type."""
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            await _start_agent(None, None)
            
            mock_console.print.assert_called()
    
    @pytest.mark.asyncio
    async def test_stop_agent_success(self):
        """Test successfully stopping an agent."""
        with patch('open_logistics.presentation.cli.main.AgentManager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_manager.initialize = AsyncMock()
            mock_manager.stop_agent = AsyncMock(return_value=True)
            
            with patch('open_logistics.presentation.cli.main.console') as mock_console:
                await _stop_agent("supply-chain")
                
                mock_console.print.assert_called()
    
    @pytest.mark.asyncio
    async def test_stop_agent_no_type(self):
        """Test stopping agent without type."""
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            await _stop_agent(None)
            
            mock_console.print.assert_called()
    
    def test_show_agent_status_specific_agent(self):
        """Test showing status for specific agent."""
        with patch('open_logistics.presentation.cli.main.asyncio.run') as mock_run:
            _show_agent_status("supply-chain")
            
            mock_run.assert_called_once()
    
    def test_show_agent_status_all_agents(self):
        """Test showing status for all agents."""
        with patch('open_logistics.presentation.cli.main.asyncio.run') as mock_run:
            _show_agent_status(None)
            
            mock_run.assert_called_once()
    
    def test_configure_agent_no_type(self):
        """Test configuring agent without type."""
        with patch('open_logistics.presentation.cli.main.console') as mock_console:
            _configure_agent(None, None)
            
            mock_console.print.assert_called()
    
    @pytest.mark.asyncio
    async def test_setup_database(self):
        """Test database setup."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            await _setup_database()
            mock_sleep.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_setup_mlx(self):
        """Test MLX setup."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            await _setup_mlx()
            mock_sleep.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_setup_monitoring(self):
        """Test monitoring setup."""
        with patch('open_logistics.presentation.cli.main.asyncio.sleep') as mock_sleep:
            await _setup_monitoring()
            mock_sleep.assert_called_once_with(1)
    
    def test_save_results(self, tmp_path):
        """Test saving results to file."""
        output_file = tmp_path / "results.json"
        result = {"test": "data", "value": 123}
        
        _save_results(result, output_file)
        
        assert output_file.exists()
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data == result 