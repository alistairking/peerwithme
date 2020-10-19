build:
	docker build -t peerwithme:latest ./

run:
	docker run --init --net=host --name peerwithme -d peerwithme:latest

clean:
	docker stop peerwithme || echo "Not running?"
	docker rm peerwithme || echo "No container?"

restart: build clean run
