cd $(dirname $0)
sh ./up-role.sh & sh ./up-network.sh & wait
sh ./up-dev.sh & ./up-prod.sh