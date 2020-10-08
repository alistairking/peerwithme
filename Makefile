build:
	docker build -t peerwithme:latest ./

run:
	docker run --init --net=host --name peerwithme -d peerwithme:latest

clean:
	docker stop peerwithme
	docker rm peerwithme

restart: build clean run
