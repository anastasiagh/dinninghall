# Dinning Hall

## Docker
1. Create docker image
```
docker build -t image1 .
```

2. Create docker communication network
```
docker network create network1
```

3. Create and run docker container on network
```
docker run -d --net --name container1 image1
```