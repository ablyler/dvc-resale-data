FROM python:3.9-slim

LABEL maintainer="ROFR Scraper Maintainers"
LABEL description="Disney Vacation Club ROFR data scraper for DisBoards"

# Set working directory
WORKDIR /app

# Install pipenv and git
RUN pip install pipenv && \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv install --system --deploy

# Copy the rest of the application
COPY . .

# Create directory for output
RUN mkdir -p /data

# Set volume for data persistence
VOLUME /data

# Default command
ENTRYPOINT ["python"]
CMD ["rofr_scraper.py", "--output", "/data/rofr_data.csv"]