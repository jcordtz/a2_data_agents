FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Install Oracle Instant Client
RUN apt-get update && apt-get install -y \
    libaio1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download and install Oracle Instant Client (required for thick mode)
# Comment out if using thin mode (oracledb default)
# RUN wget https://download.oracle.com/otn_software/linux/instantclient/2110000/instantclient-basic-linux.x64-21.10.0.0.0dbru.zip \
#     && unzip instantclient-basic-linux.x64-21.10.0.0.0dbru.zip -d /opt/oracle \
#     && rm instantclient-basic-linux.x64-21.10.0.0.0dbru.zip
# ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_10:$LD_LIBRARY_PATH

# Set working directory
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

COPY . /home/site/wwwroot
