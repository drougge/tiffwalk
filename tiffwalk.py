#!/usr/bin/env python3
#
# Walk all the sections in a TIFF file looking for a specific value. The
# use case I had for this is to find something in a DNG file (which is a
# TIFF file).
#
# Most files of interest probably have sections with tagged data that is
# not marked as such (makernotes and similar). There is currently no
# support for walking those (and no standard way of finding or walking
# them).

from __future__ import print_function

class TIFF:
	"""Partial TIFF(ish) container parser (mostly taken from wellpapp)"""
	
	types = { 1: (1, "B"),  # BYTE
	          2: (1, None), # ASCII
	          3: (2, "H"),  # SHORT
	          4: (4, "I"),  # LONG
	          5: (8, "II"), # RATIONAL
	          6: (1, "b"),  # SBYTE
	          7: (1, None), # UNDEFINE
	          8: (2, "h"),  # SSHORT
	          9: (4, "i"),  # SLONG
	         10: (8, "ii"), # SRATIONAL
	         11: (4, "f"),  # FLOAT
	         12: (8, "d"),  # DOUBLE 13: (4, "I"),  # IFD
	        }
	
	def __init__(self, fh, allow_variants=True):
		from struct import unpack
		self._fh = fh
		d = fh.read(4)
		good = [b"II*\0", b"MM\0*"]
		if allow_variants:
			# Olympus ORF, Panasonic RW2
			good += [b"IIRO", b"IIU\0"]
		if d not in good: raise Exception("Not TIFF")
		self.variant = d[2:4].strip(b"\0")
		endian = {77: ">", 73: "<"}[d[0]]
		self._up = lambda fmt, *a: unpack(endian + fmt, *a)
		self._up1 = lambda *a: self._up(*a)[0]
		next_ifd = self._up1("I", fh.read(4))
		# Be conservative with possibly mis-detected ORF
		if self.variant == "RO":
			assert next_ifd == 8
		self.reinit_from(next_ifd)
	
	def reinit_from(self, next_ifd):
		self.ifd = []
		self.subifd = []
		seen_ifd = set()
		while next_ifd:
			self.ifd.append(self._ifdread(next_ifd))
			next_ifd = self._up1("I", self._fh.read(4))
			if next_ifd in seen_ifd:
				from sys import stderr
				print("WARNING: Looping IFDs", file=stderr)
				break
			seen_ifd.add(next_ifd)
			assert len(self.ifd) < 32 # way too many
		subifd = self.ifdget(self.ifd[0], 0x14a) or []
		assert len(subifd) < 32 # way too many
		for next_ifd in subifd:
			self.subifd.append(self._ifdread(next_ifd))
	
	def ifdget(self, ifd, tag):
		if tag in ifd:
			type, vc, off = ifd[tag]
			if type not in self.types: return None
			if isinstance(off, int): # offset
				self._fh.seek(off)
				tl, fmt = self.types[type]
				off = self._fh.read(tl * vc)
				if fmt: off = self._up(fmt * vc, off)
			if type == 2:
				off = off.rstrip(b"\0")
			return off
	
	def _ifdread(self, next_ifd):
		ifd = {}
		self._fh.seek(next_ifd)
		count = self._up1("H", self._fh.read(2))
		for i in range(count):
			d = self._fh.read(12)
			tag, type, vc = self._up("HHI", d[:8])
			if type in self.types and self.types[type][0] * vc <= 4:
				tl, fmt = self.types[type]
				d = d[8:8 + (tl * vc)]
				if fmt:
					off = self._up(fmt * vc, d)
				else:
					off = d # ASCII
			else:
				off = self._up1("I", d[8:])
			ifd[tag] = (type, vc, off)
		return ifd

def show(prefix, tag):
	print(" ".join(str(v) for v in prefix + [tag]))

todo = []
def ifdwalk(tiff, prefix, find_value):
	ifds = [([(idx,)], ifd) for idx, ifd in enumerate(tiff.ifd)]
	subifds = [([(0x14a, idx)], ifd) for idx, ifd in enumerate(tiff.subifd)]
	for midfix, ifd in ifds + subifds:
		local_prefix = prefix + midfix
		for tag in ifd:
			value = tiff.ifdget(ifd, tag)
			if ifd[tag][0] == 13: # another ifd
				for idx, sub in enumerate(value):
					todo.append((local_prefix + [(tag, idx,)], sub,))
			else:
				if isinstance(value, bytes):
					if isinstance(find_value, bytes):
						if find_value in value:
							show(local_prefix, tag)
				else:
					if find_value in value:
						show(local_prefix, tag)

def tiffwalk(fh, find_value):
	tiff = TIFF(fh)
	ifdwalk(tiff, [], find_value)
	while todo:
		prefix, off = todo.pop()
		tiff.reinit_from(off)
		ifdwalk(tiff, prefix, find_value)

if __name__ == "__main__":
	from sys import argv, stderr, exit
	if len(argv) != 3:
		print("Usage: %s tiff-file value" % (argv[0],), file=stderr)
		exit(1)
	find_value = argv[2]
	try:
		find_value = int(find_value)
	except ValueError:
		find_value = find_value.encode("UTF-8")
	with open(argv[1], "rb") as fh:
		tiffwalk(fh, find_value)
