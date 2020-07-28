from math import nan

def split_well_name(name):
	for i,c in enumerate(name):
		if c.isnumeric():
			break
	return name[:i],int(name[i:])

def to_seconds(time):
	hours, minutes, seconds = map(int,time.split(":"))
	return (hours*60+minutes)*60 + seconds

def parse_number(string):
	if string:
		return float(string)
	else:
		return nan

class LineBuffer(object):
	def __init__(self,lines):
		self.lines = lines
		self.pos = 0
	
	def clear_empty_lines(self):
		while self.lines and self.lines[0]=="":
			self.lines.pop(0)
	
	def __iter__(self):
		self.clear_empty_lines()
		for self.pos,line in enumerate(self.lines):
			yield line
	
	def clear(self):
		del self.lines[:self.pos]
	
	def __bool__(self):
		self.clear_empty_lines()
		return bool(self.lines)

