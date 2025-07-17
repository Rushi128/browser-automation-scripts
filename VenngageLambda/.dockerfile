FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum install -y \
    wget \
    unzip \
    xorg-x11-server-Xvfb \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXtst \
    alsa-lib \
    atk \
    cups-libs \
    gtk3 \
    ipa-gothic-fonts \
    libXrandr \
    libXss \
    libXScrnSaver \
    pango \
    xdg-utils

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Install Playwright and its dependencies
RUN pip3 install playwright && \
    playwright install --with-deps chromium

# Copy function code
COPY main.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (main.lambda_handler)
CMD ["main.lambda_handler"]
