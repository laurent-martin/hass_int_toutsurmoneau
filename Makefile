all::
bumpver:
	bumpver update --patch
release:
	gh release create
prepare:
	python3 -m venv .env
	source .env/bin/activate &&\
		pip install --upgrade pip &&\
		pip install homeassistant
start:
	echo "http://localhost:8123"
	mkdir -p ~/.homeassistant/custom_components/
	cp -r custom_components ~/.homeassistant
	source .env/bin/activate && hass
