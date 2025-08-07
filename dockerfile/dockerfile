# Use the official Qdrant Docker image
FROM qdrant/qdrant:v1.2.0

# Expose the port Qdrant runs on
EXPOSE 6333

# Set the storage directory
ENV QDRANT__STORAGE__DIR=/data

# Create the storage directory
RUN mkdir -p /data

# Start Qdrant
CMD ["qdrant"]
