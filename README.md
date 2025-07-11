# Browser Automation Scripts

A Docker-based browser automation solution using Selenium and Chrome, designed for AWS Lambda deployment.

## Overview

This repository contains browser automation scripts that can be deployed as AWS Lambda functions using Docker containers. The solution includes Chrome browser automation capabilities with Selenium WebDriver.

## Files

- `Dockerfile` - Container configuration for AWS Lambda Python runtime
- `main.py` - Main Lambda handler function
- `chrome-installer.sh` - Script to install Chrome browser in the container
- `venngagescript.py` - Venngage automation script
- `workingscriptofpicktochart.py` - PiktoChart automation script
- `steps.txt` - Documentation of deployment steps
- `playwrights/` - Directory containing Playwright-related files

## Features

- Chrome browser automation with Selenium
- AWS Lambda compatible Docker container
- Pre-configured Chrome dependencies
- Python 3.12 runtime
- ECR integration for container deployment

## Prerequisites

- Docker
- AWS CLI configured with appropriate permissions
- Access to AWS ECR repository

## Build and Deploy

### Build Docker Image
```bash
docker build -t browser-automation-scripts:latest .
```

### Tag for ECR
```bash
docker tag browser-automation-scripts:latest 277707134536.dkr.ecr.ap-south-1.amazonaws.com/browser-automation-scripts-images:v1.0.2
```

### Push to ECR
```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 277707134536.dkr.ecr.ap-south-1.amazonaws.com
docker push 277707134536.dkr.ecr.ap-south-1.amazonaws.com/browser-automation-scripts-images:v1.0.2
```

## Usage

The main Lambda function is defined in `main.py` and can be invoked with appropriate event data.

## Dependencies

- selenium
- requests
- boto3
- Chrome browser
- Chrome dependencies (installed via chrome-installer.sh)

## License

This project is for internal use and automation purposes.

## Last Updated

July 11, 2025
