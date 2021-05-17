from math import nan
from string import ascii_uppercase

def split_well_name(name):
	if name=="":
		raise ValueError("Not a proper well name")
	
	for i,c in enumerate(name):
		if c.isnumeric():
			break
	col = name[:i]
	row = int(name[i:])
	
	if not col.isalpha():
		raise ValueError("Not a proper well name")
	
	return col,row

def extract_channel(string):
	name,_,channel = string.partition("[")
	if not channel or channel[-1] != "]":
		raise ValueError
	channel = channel[:-1]
	name = name.rstrip()
	return name,channel

def parse_time(time):
	if time=="?????":
		return nan
	else:
		hours, minutes, seconds = map(int,time.split(":"))
		return (hours*60+minutes)*60 + seconds

def parse_number(string):
	if string:
		return float(string)
	else:
		return nan

def parse_timestamp(string):
	if not string.startswith("Time"):
		raise ValueError
	string = string[4:].strip()
	number, _, time = string.partition(" (")
	number = int(number)
	if not time or time[-1] != ")":
		raise ValueError
	time = parse_time(time[:-1])
	return number, time

def row_iter():
	for letter in ascii_uppercase:
		yield letter
	for letter_1 in ascii_uppercase:
		for letter_2 in ascii_uppercase:
			yield letter_1+letter_2

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
		del self.lines[:self.pos+1]
	
	def __bool__(self):
		self.clear_empty_lines()
		return bool(self.lines)
	
	def __enter__(self):
		return iter(self)
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		if exc_type is None:
			self.clear()

