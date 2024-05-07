cd $(dirname $0)
pulumi up --stack=quanduongduc/fastapi-ecs/prod --cwd=../infrastructure/ecs/ --yes