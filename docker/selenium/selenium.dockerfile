FROM python:3.11-slim

ARG CHROME_VERSION=136.0.7103.92        # Google Chrome y ChromeDriver
ARG CHROME_DEB_REV=1                    # sufijo «-1»
ARG SELENIUM_VERSION=4.32.0             # versión de Selenium

# Sistema + Google Chrome + ChromeDriver
RUN set -eux; \
    # ---------------------- dependencias de sistema -----------------------
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl wget unzip gnupg \
    fonts-liberation libnss3 libxss1 libappindicator3-1 \
    libasound2 libatk-bridge2.0-0 libgtk-3-0 \
    libx11-xcb1 libxcb-dri3-0 libdrm2 libgbm1 \
    libxcomposite1 libxdamage1 libxrandr2 \
    libu2f-udev libvulkan1 && \
    # ------------------------- Google Chrome fijo -------------------------
    DEB_FILE="google-chrome-stable_${CHROME_VERSION}-${CHROME_DEB_REV}_amd64.deb" && \
    wget -q "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/${DEB_FILE}" \
    -O "/tmp/${DEB_FILE}" && \
    apt-get install -y "/tmp/${DEB_FILE}" && \
    rm "/tmp/${DEB_FILE}" && \
    # ------------------------- ChromeDriver fijo -------------------------
    DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    wget -q -O /tmp/chromedriver.zip "${DRIVER_URL}" && \
    unzip -q /tmp/chromedriver.zip -d /tmp && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver* && \
    # ----------------------------- limpieza ------------------------------
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY examples/ /app/examples/

CMD ["sleep", "infinity"]
