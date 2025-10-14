# Use the official Immich image as our starting point
# You can replace the tag with the specific version you are using
FROM ghcr.io/immich-app/immich-machine-learning:v2.0.1-rocm

# Switch to root user to install packages
USER root

# Add the AMD GPU repository for Ubuntu 22.04 (used by the base image)
# This will provide the latest ROCm packages
RUN apt-get update && apt-get install -y wget gnupg
RUN wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key | apt-key add -
RUN echo "deb [arch=amd64] https://repo.radeon.com/rocm/apt/6.4.4/ ubuntu main" | tee /etc/apt/sources.list.d/rocm.list

# Update package lists and install/upgrade to the latest ROCm
# This will overwrite the older ROCm version with the new one
RUN apt-get update && \
    apt-get install -y --allow-downgrades \
    rocm-hip-sdk \
    rocm-libs \
    rocm-onnxruntime && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch back to the non-root user that Immich runs as
USER immich