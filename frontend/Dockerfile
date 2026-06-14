FROM node:20-slim

WORKDIR /app

COPY package.json ./
# Sin package-lock todavía: usamos install. En CI/prod conviene `npm ci` con lockfile.
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
