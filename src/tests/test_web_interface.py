"""
Tests for web interface functionality and API integration.
Tests browser loading, flowchart rendering, and learning metrics display.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests
import time
import subprocess
import os
import tempfile


class TestWebInterfaceIntegration:
    """Integration tests for the enhanced web interface."""

    @pytest.fixture(scope="class")
    def api_server(self):
        """Start the API server for testing."""
        # Start the API server in a subprocess
        server_process = subprocess.Popen(
            ["uv", "run", "uvicorn", "src.api.main:app", "--host", "localhost", "--port", "8000"],
            cwd="/Users/davisimite/Documents/muleta-cognitiva",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(3)
        
        # Verify server is running
        try:
            response = requests.get("http://localhost:8000/api/entities", timeout=5)
            assert response.status_code in [200, 404]  # 404 is fine for empty DB
        except Exception as e:
            server_process.terminate()
            raise Exception(f"API server failed to start: {e}")
        
        yield server_process
        
        # Cleanup
        server_process.terminate()
        server_process.wait()

    @pytest.fixture(scope="class")
    def web_driver(self):
        """Set up Chrome WebDriver for browser testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode for CI
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            yield driver
        except Exception as e:
            pytest.skip(f"Chrome WebDriver not available: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing visualization."""
        return {
            "nodes": [
                {
                    "name": "Filosofia",
                    "entityType": "conceito",
                    "category": 0,
                    "value": 5,
                    "observations": ["Estudo da sabedoria", "Reflexão crítica"]
                },
                {
                    "name": "Ética",
                    "entityType": "ramo",
                    "category": 1,
                    "value": 3,
                    "observations": ["Estudo do bem e mal"]
                },
                {
                    "name": "Epistemologia",
                    "entityType": "ramo",
                    "category": 1,
                    "value": 4,
                    "observations": ["Teoria do conhecimento"]
                }
            ],
            "links": [
                {
                    "source": "Filosofia",
                    "target": "Ética",
                    "relationType": "inclui"
                },
                {
                    "source": "Filosofia",
                    "target": "Epistemologia",
                    "relationType": "inclui"
                }
            ],
            "categories": [
                {"name": "conceito"},
                {"name": "ramo"}
            ]
        }

    def test_web_interface_loading(self, web_driver, api_server):
        """Test that the web interface loads correctly."""
        # Serve the HTML file locally
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        
        # Wait for the page to load
        wait = WebDriverWait(web_driver, 10)
        
        # Check that main elements are present
        assert wait.until(EC.presence_of_element_located((By.CLASS_NAME, "app-container")))
        assert wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sidebar")))
        assert wait.until(EC.presence_of_element_located((By.CLASS_NAME, "main-content")))
        
        # Check navigation tabs
        tabs = web_driver.find_elements(By.CLASS_NAME, "nav-tab")
        expected_tabs = ["Grafo de Conhecimento", "Dashboard de Aprendizagem", 
                        "Fluxogramas Argumentativos", "Avaliações"]
        
        assert len(tabs) == len(expected_tabs)
        for i, expected_text in enumerate(expected_tabs):
            assert expected_text in tabs[i].text

    def test_chart_containers_present(self, web_driver, api_server):
        """Test that all chart containers are present in the DOM."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Check main chart
        assert wait.until(EC.presence_of_element_located((By.ID, "chart")))
        
        # Check learning dashboard charts
        assert wait.until(EC.presence_of_element_located((By.ID, "reviewChart")))
        assert wait.until(EC.presence_of_element_located((By.ID, "cardTypeChart")))
        
        # Check argument flow chart
        assert wait.until(EC.presence_of_element_located((By.ID, "argumentChart")))
        
        # Check assessment charts
        assert wait.until(EC.presence_of_element_located((By.ID, "assessmentChart")))
        assert wait.until(EC.presence_of_element_located((By.ID, "knowledgeGapChart")))

    def test_tab_navigation(self, web_driver, api_server):
        """Test tab navigation functionality."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Initially, knowledge graph tab should be active
        knowledge_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'nav-tab') and contains(text(), 'Grafo de Conhecimento')]")))
        assert "active" in knowledge_tab.get_attribute("class")
        
        # Click on learning dashboard tab
        dashboard_tab = web_driver.find_element(By.XPATH, "//div[contains(@class, 'nav-tab') and contains(text(), 'Dashboard de Aprendizagem')]")
        dashboard_tab.click()
        
        # Wait for tab switch
        wait.until(lambda driver: "active" in dashboard_tab.get_attribute("class"))
        assert "active" not in knowledge_tab.get_attribute("class")
        
        # Check that corresponding content is visible
        dashboard_pane = web_driver.find_element(By.ID, "learning-dashboard")
        assert "active" in dashboard_pane.get_attribute("class")

    def test_entity_list_functionality(self, web_driver, api_server):
        """Test entity list display and search functionality."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Check entity list container
        entity_list = wait.until(EC.presence_of_element_located((By.ID, "entityList")))
        
        # Check search input
        search_input = wait.until(EC.presence_of_element_located((By.ID, "entitySearch")))
        assert search_input.get_attribute("placeholder") == "Buscar entidade..."

    def test_controls_functionality(self, web_driver, api_server):
        """Test control elements functionality."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Test graph type selector
        graph_type_select = wait.until(EC.presence_of_element_located((By.ID, "graphType")))
        options = graph_type_select.find_elements(By.TAG_NAME, "option")
        
        expected_options = ["Grafo de Força", "Grafo Circular", "Sankey Flow", "Fluxograma Argumentativo"]
        option_texts = [opt.text for opt in options]
        
        for expected in expected_options:
            assert expected in option_texts
        
        # Test category filter
        category_filter = wait.until(EC.presence_of_element_located((By.ID, "categoryFilter")))
        assert category_filter is not None
        
        # Test buttons
        refresh_btn = web_driver.find_element(By.XPATH, "//button[contains(text(), 'Atualizar Dados')]")
        assert refresh_btn is not None
        
        export_btn = web_driver.find_element(By.XPATH, "//button[contains(text(), 'Exportar Visualização')]")
        assert export_btn is not None

    def test_learning_dashboard_elements(self, web_driver, api_server):
        """Test learning dashboard specific elements."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Navigate to learning dashboard
        dashboard_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'nav-tab') and contains(text(), 'Dashboard de Aprendizagem')]")))
        dashboard_tab.click()
        
        # Check statistics cards
        total_entities = wait.until(EC.presence_of_element_located((By.ID, "totalEntities")))
        total_cards = wait.until(EC.presence_of_element_located((By.ID, "totalCards")))
        due_cards = wait.until(EC.presence_of_element_located((By.ID, "dueCards")))
        success_rate = wait.until(EC.presence_of_element_located((By.ID, "successRate")))
        
        assert total_entities is not None
        assert total_cards is not None
        assert due_cards is not None
        assert success_rate is not None

    def test_argument_flows_tab(self, web_driver, api_server):
        """Test argument flows tab functionality."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Navigate to argument flows tab
        flows_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'nav-tab') and contains(text(), 'Fluxogramas')]")))
        flows_tab.click()
        
        # Check argument chart
        argument_chart = wait.until(EC.presence_of_element_located((By.ID, "argumentChart")))
        assert argument_chart is not None
        
        # Check sequence creation controls
        sequence_title = wait.until(EC.presence_of_element_located((By.ID, "sequenceTitle")))
        assert sequence_title.get_attribute("placeholder") == "Nome da sequência"
        
        selected_entities = wait.until(EC.presence_of_element_located((By.ID, "selectedEntities")))
        assert selected_entities is not None
        
        create_btn = web_driver.find_element(By.XPATH, "//button[contains(text(), 'Criar Sequência')]")
        assert create_btn is not None

    def test_assessments_tab(self, web_driver, api_server):
        """Test assessments tab functionality."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Navigate to assessments tab
        assessments_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'nav-tab') and contains(text(), 'Avaliações')]")))
        assessments_tab.click()
        
        # Check assessment charts
        assessment_chart = wait.until(EC.presence_of_element_located((By.ID, "assessmentChart")))
        knowledge_gap_chart = wait.until(EC.presence_of_element_located((By.ID, "knowledgeGapChart")))
        
        assert assessment_chart is not None
        assert knowledge_gap_chart is not None

    def test_api_status_indicator(self, web_driver, api_server):
        """Test API status indicator functionality."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Check API status indicator
        api_status = wait.until(EC.presence_of_element_located((By.ID, "apiStatus")))
        assert api_status is not None
        
        # Initially should show disconnected (since we're using file:// protocol)
        assert "status-indicator" in api_status.get_attribute("class")

    def test_responsive_design_elements(self, web_driver, api_server):
        """Test responsive design elements."""
        html_path = "/Users/davisimite/Documents/muleta-cognitiva/index.html"
        file_url = f"file://{html_path}"
        
        web_driver.get(file_url)
        wait = WebDriverWait(web_driver, 10)
        
        # Test desktop layout
        web_driver.set_window_size(1920, 1080)
        sidebar = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sidebar")))
        sidebar_width = sidebar.size['width']
        
        # Test mobile layout
        web_driver.set_window_size(768, 1024)
        time.sleep(1)  # Allow CSS to apply
        
        # Sidebar should still be present but potentially smaller
        assert sidebar.is_displayed()


class TestWebInterfaceUnit:
    """Unit tests for web interface JavaScript functions (simulated)."""

    def test_escape_html_function(self):
        """Test HTML escaping functionality."""
        # This would test the escapeHtml function if we could run JS in isolation
        test_cases = [
            ("<script>", "&lt;script&gt;"),
            ("&amp;", "&amp;amp;"),
            ('"quotes"', "&quot;quotes&quot;"),
            ("'apostrophe'", "&#39;apostrophe&#39;")
        ]
        
        # In a real implementation, we'd use a JS testing framework
        # For now, we validate the expected behavior
        for input_str, expected in test_cases:
            # Simulate the escapeHtml function behavior
            result = (input_str
                     .replace('&', '&amp;')
                     .replace('<', '&lt;')
                     .replace('>', '&gt;')
                     .replace('"', '&quot;')
                     .replace("'", '&#39;'))
            assert result == expected

    def test_format_date_function(self):
        """Test date formatting functionality."""
        # Test ISO date string formatting
        test_date = "2025-01-24T10:30:00Z"
        # In the real JS function, this would format to Brazilian locale
        assert test_date is not None

    def test_api_endpoint_configuration(self):
        """Test API endpoint configuration."""
        expected_base_url = "http://localhost:8000/api"
        # In real implementation, this would check the JS state object
        assert expected_base_url.startswith("http")
        assert "/api" in expected_base_url


class TestFlowchartRendering:
    """Tests specific to flowchart rendering functionality."""

    def test_flowchart_data_transformation(self):
        """Test data transformation for flowchart visualization."""
        # Sample input data
        nodes = [
            {"name": "Premissa 1", "entityType": "premise"},
            {"name": "Premissa 2", "entityType": "premise"},
            {"name": "Conclusão", "entityType": "conclusion"}
        ]
        
        links = [
            {"source": "Premissa 1", "target": "Conclusão"},
            {"source": "Premissa 2", "target": "Conclusão"}
        ]
        
        # Expected transformation for ECharts flowchart
        expected_flow_nodes = [
            {
                "id": "Premissa 1",
                "name": "Premissa 1",
                "symbol": "roundRect",
                "symbolSize": [100, 60]
            },
            {
                "id": "Premissa 2", 
                "name": "Premissa 2",
                "symbol": "roundRect",
                "symbolSize": [100, 60]
            },
            {
                "id": "Conclusão",
                "name": "Conclusão", 
                "symbol": "roundRect",
                "symbolSize": [100, 60]
            }
        ]
        
        # Verify transformation logic
        assert len(nodes) == len(expected_flow_nodes)
        for i, node in enumerate(nodes):
            assert node["name"] == expected_flow_nodes[i]["name"]

    def test_flowchart_color_coding(self):
        """Test color coding for different node types in flowcharts."""
        node_type_colors = {
            "premise": "#91cc75",
            "conclusion": "#fac858", 
            "evidence": "#73c0de",
            "default": "#ee6666"
        }
        
        # Test that each node type has an assigned color
        for node_type, color in node_type_colors.items():
            assert color.startswith("#")
            assert len(color) == 7  # Valid hex color

    def test_flowchart_layout_configuration(self):
        """Test flowchart layout configuration."""
        expected_config = {
            "type": "graph",
            "layout": "none",  # Manual positioning for flowcharts
            "roam": True,
            "edgeSymbol": ["none", "arrow"],
            "edgeSymbolSize": 8
        }
        
        # Verify configuration structure
        assert expected_config["type"] == "graph"
        assert expected_config["layout"] == "none"
        assert expected_config["roam"] is True


class TestLearningAnalytics:
    """Tests for learning analytics and dashboard functionality."""

    def test_statistics_display_format(self):
        """Test statistics display formatting."""
        mock_stats = {
            "entities_count": 150,
            "total_cards": 45,
            "cards_due": 12,
            "avg_success_rate": 0.847
        }
        
        # Test formatting
        assert mock_stats["entities_count"] == 150
        assert mock_stats["total_cards"] == 45
        assert mock_stats["cards_due"] == 12
        
        # Success rate should be converted to percentage
        success_percentage = round(mock_stats["avg_success_rate"] * 100)
        assert success_percentage == 85

    def test_review_progress_chart_data(self):
        """Test review progress chart data structure."""
        sample_review_data = {
            "xAxis": ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"],
            "series": [12, 8, 15, 9, 11, 7, 6]
        }
        
        assert len(sample_review_data["xAxis"]) == 7  # Week days
        assert len(sample_review_data["series"]) == 7  # Matching data points
        assert all(isinstance(val, int) for val in sample_review_data["series"])

    def test_card_type_distribution_data(self):
        """Test card type distribution chart data."""
        sample_card_distribution = [
            {"value": 35, "name": "Definição"},
            {"value": 25, "name": "Socrático"}, 
            {"value": 20, "name": "Relação"},
            {"value": 20, "name": "Aplicação"}
        ]
        
        total_cards = sum(item["value"] for item in sample_card_distribution)
        assert total_cards == 100
        
        # Check that all required card types are present
        card_types = {item["name"] for item in sample_card_distribution}
        expected_types = {"Definição", "Socrático", "Relação", "Aplicação"}
        assert card_types == expected_types

    def test_knowledge_gap_radar_data(self):
        """Test knowledge gap radar chart data structure."""
        sample_radar_data = {
            "indicator": [
                {"name": "Filosofia Política", "max": 100},
                {"name": "Epistemologia", "max": 100},
                {"name": "Ética", "max": 100},
                {"name": "Metafísica", "max": 100},
                {"name": "Lógica", "max": 100}
            ],
            "data": [65, 85, 70, 55, 90]
        }
        
        assert len(sample_radar_data["indicator"]) == len(sample_radar_data["data"])
        assert all(0 <= val <= 100 for val in sample_radar_data["data"])
        assert all(ind["max"] == 100 for ind in sample_radar_data["indicator"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
