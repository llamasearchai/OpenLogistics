# Getting Started

This guide will help you get up and running with Open Logistics quickly.

## Prerequisites

- Python 3.9 or higher
- macOS (for MLX optimization) or Linux/Windows
- 8GB+ RAM recommended
- Git

## Installation

### Method 1: Using uv (Recommended)


# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/openlogistics/open-logistics.git
cd open-logistics
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev,mlx]" 