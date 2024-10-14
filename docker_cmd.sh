tag=1.0.3
# docker 构建镜像
docker build -t ai-asst:${tag} .

# docker 启动
docker run --name ai-asst${tag} --restart=always -d -p 7999:7999 ai-asst:${tag}

# docker 查看 log
docker logs -f ai-asst${tag}

# docker 进入镜像
# docker exec -it ai-asst:${tag} bash

