# Use official Node.js image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the source
COPY . .

# Expose port and start app
EXPOSE 3000
CMD ["npm", "run", "dev"]
