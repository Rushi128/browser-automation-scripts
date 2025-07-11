FROM amazon/aws-lambda-python:3.12
RUN dnf install -y \
    gtk3 libXtst libXScrnSaver libXrandr libXcomposite libXdamage libXcursor \
    libXext libXi alsa-lib at-spi2-atk cups-libs libXt pango xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm jq unzip wget tar xz \
    && dnf clean all

RUN wget -O firefox.tar.xz "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US" \
    && tar -xJf firefox.tar.xz -C /opt/ \
    && ln -s /opt/firefox/firefox /usr/local/bin/firefox \
    && rm firefox.tar.xz

RUN GECKODRIVER_VERSION=$(wget -qO- https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep '"tag_name"' | cut -d'"' -f4) \
    && wget -O geckodriver.tar.gz "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && tar -xzf geckodriver.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver \
    && rm geckodriver.tar.gz

RUN pip install selenium requests boto3

COPY main.py ./
CMD ["main.lambda_handler"]