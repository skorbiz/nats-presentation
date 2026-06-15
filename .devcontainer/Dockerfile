# FROM mcr.microsoft.com/.devcontainer/mezcada-defaults/base:jammy
FROM ubuntu:24.04

# Install core development tools and utilities:
# - Python 3.12 with pip, venv, and dev headers
# - Docker CLI, Git, and version control tools
# - Network utilities (ping, nmap, ip, ssh, rsync)
# - Build tools (gcc, build-essential) for Python packages and pre-commit hooks
# - Shell tools (bash-completion, shellcheck, nano, jq, yq)
# - Development utilities (meld, liburdfdom-tools)
# - Package management (wget, unzip, curl) for Terraform and other tools
RUN export DEBIAN_FRONTEND=noninteractive && apt-get update && apt-get install -y --no-install-recommends \
 bash-completion \
 python3 \
 python3-pip \
 python3.12-venv \
 python3.12-dev \
 software-properties-common \
 curl \
 sudo \
 docker.io \
 docker-buildx \
 git \
 gh \
 jq \
 yq \
 shellcheck \
 meld \
 iputils-ping \
 nmap \
 iproute2 \
 nano \
 ssh-client \
 build-essential \
 gcc \
 wget \
 unzip
 
# Install Node.js 24.x (includes npm from NodeSource)
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
 && apt-get update \
 && apt-get install -y --no-install-recommends nodejs

# Install Playwright system dependencies
RUN npx -y playwright install-deps

# Install UV 0.11.2 for python package management
RUN curl -LsSf https://astral.sh/uv/0.11.2/install.sh | UV_INSTALL_DIR=/usr/local/bin sh

# Install Python dev requirements like ruff and pyrefly
# COPY requirements-dev.txt /tmp/requirements-dev.txt
# RUN python3 -m pip install --break-system-packages -r /tmp/requirements-dev.txt \
#  && rm /tmp/requirements-dev.txt

 # Set users
# Ubuntu 24.04 adding a default user named ubuntu with gid and uid 1000
# Rename the ubuntu user to dev, move the home directory, and change the group. Obs this assumes uid and gid 1000.
# https://askubuntu.com/questions/1513927/ubuntu-24-04-docker-images-now-includes-user-ubuntu-with-uid-gid-1000
# https://www.serverlab.ca/tutorials/linux/administration-linux/how-to-rename-linux-users-and-their-home-directory/
RUN usermod -l dev ubuntu
RUN usermod -d /home/dev -m dev
RUN groupmod -n dev ubuntu

RUN echo 'dev:Docker!' | chpasswd
RUN echo 'root:Docker!' | chpasswd
RUN usermod --append --groups systemd-journal dev
# Allow dev user to run apt/apt-get without password for dotfiles installation scripts
RUN echo 'dev ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get' >> /etc/sudoers
# Create mount targets with correct ownership so Docker does not create them as root.
RUN install -d -o dev -g dev -m 700 /home/dev/.ssh /home/dev/.config/gh /home/dev/.copilot /home/dev/.balena \
 && install -d -o dev -g dev -m 755 /workspaces/mezcada/docs/mezcada-pages/node_modules
WORKDIR /home/dev


# Install Copilot CLI (https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)
ARG COPILOT_VERSION=latest
RUN curl -fsSL https://gh.io/copilot-install | VERSION=${COPILOT_VERSION} bash


# Cleanup
RUN rm -rf /root/.cache/pip/*. \
 && rm -rf /var/lib/apt/lists/*
