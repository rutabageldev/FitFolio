# Use official Node.js image
FROM node:20-alpine
WORKDIR /workspaces/fitfolio/frontend
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
