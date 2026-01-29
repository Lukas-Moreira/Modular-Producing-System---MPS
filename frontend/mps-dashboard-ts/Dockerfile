FROM node:20 AS build
WORKDIR /app
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
COPY package*.json ./
RUN npm install
COPY . .
# Build will pick up REACT_APP_API_URL from ENV at build time
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]