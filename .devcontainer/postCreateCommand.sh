poetry install

echo alias oidc-add=\'docker exec -it \${OIDC_AGENT_CONTAINER_NAME} oidc-add\' >> /home/node/.bashrc
echo alias oidc-gen=\'docker exec -it \${OIDC_AGENT_CONTAINER_NAME} oidc-gen\' >> /home/node/.bashrc
echo alias oidc-token=\'docker exec \${OIDC_AGENT_CONTAINER_NAME} oidc-token\' >> /home/node/.bashrc
