deploy:
	docker compose build --force-rm --progress plain
	docker compose push
	docker stack deploy --compose-file docker-compose.yml --with-registry-auth place 