all::
bumpver:
	bumpver update --patch
release:
	gh release create
