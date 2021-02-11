build-deps:
	docker build -t peerwithme-gobgp:latest ./gobgp/

build-%: build-deps
	docker build -t peerwithme-$*:latest ./$*/

run-%:
	docker run --init --net=host --name peerwithme-$* -d peerwithme-$*:latest

clean-%:
	@echo "Stopping peerwithme-$*"
	@docker stop peerwithme-$* || echo "$* not running?"
	@echo "Removing peerwithme-$*"
	@docker rm peerwithme-$* || echo "No $* container?"

.PHONY: restart-gobgpd
restart-gobgpd: build-gobgpd clean-gobgpd run-gobgpd

.PHONY: restart-proxy
restart-proxy: build-proxy clean-proxy run-proxy
