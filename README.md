Walk all the sections in a TIFF file looking for a specific value. The use
case I had for this is to find a specific value in a DNG file (which is a
TIFF file).

Most files of interest probably have sections with tagged data that is not
marked as such (makernotes and similar). There is currently no support for
walking those (and no standard way of finding or walking them).

Usage: tiffwalk.py tiff-name value

Value can be an integer or a string.

The output is not fantastically convenient. It shows you

	(SECTION_TAG, INDEX)* TAG

with everything in decimal. So for example:

	(330, 1) 256

is section 330 ("subifd"), index 1 (second one), tag 256.
So thats the width of the second subimage.

Things in the top ifd come out as

	(INEDX,) TAG
