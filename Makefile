build:
	docker build -t peerwithme:latest ./

run:
	docker run --init --net=host --name peerwithme -d peerwithme:latest
