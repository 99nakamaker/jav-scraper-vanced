# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Commands

- **Install dependencies**: This project uses Poetry for dependency management. To install dependencies, run:
  ```bash
  poetry install
  ```
- **Run the application**: The main application can be run using the `javsp` command.
  ```bash
  poetry run javsp
  ```
- **View help**: To see the available command-line arguments, run:
  ```bash
  poetry run javsp -h
  ```
- **Configuration**: The application is configured using the `config.yml` file. Open this file in a text editor to customize the application's behavior.

## Code Architecture

- **`javsp/`**: This directory contains the main source code for the JavSP application.
- **`tools/`**: This directory contains utility scripts, such as for migrating configuration files.
- **`unittest/`**: This directory contains unit tests for the project.
- **`pyproject.toml`**: This file defines the project's dependencies and other metadata for Poetry.
- **`config.yml`**: The main configuration file for the application.
