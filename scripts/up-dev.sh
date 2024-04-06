cd $(dirname $0)
pulumi up --stack=quanduongduc/fastapi-ecs/dev --cwd=../deployment/infrastructure/ecs/ --yes