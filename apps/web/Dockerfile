FROM node:22-alpine

WORKDIR /workspace

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev:web", "--", "--host", "0.0.0.0"]
