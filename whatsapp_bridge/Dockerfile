FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Expose port 3000
EXPOSE 3000

# Create temp media directory
RUN mkdir -p temp_media

CMD ["node", "index.js"]
