FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget unzip curl jq \
    libnss3 libatk1.0-0 libcups2 libxcomposite1 libxrandr2 libxdamage1 \
    libxext6 libxfixes3 libx11-xcb1 libxss1 libxtst6 libx11-dev libxrender1 \
    libxi6 libgtk-3-0 libasound2 libdbus-glib-1-2 libgbm1 libxshmfence1 \
    fonts-liberation libappindicator3-1 libxt6 libxinerama1 xauth xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Lambda Runtime Interface Client (RIC)
RUN curl -Lo /usr/local/bin/aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie && \
    chmod +x /usr/local/bin/aws-lambda-rie

# Install Playwright
RUN pip install --no-cache-dir playwright && playwright install chromium

# Add application code
COPY main.py ./

# Set the entrypoint for Lambda
ENTRYPOINT ["/usr/local/bin/aws-lambda-rie", "python", "-m", "awslambdaric"]

CMD ["main.lambda_handler"]
