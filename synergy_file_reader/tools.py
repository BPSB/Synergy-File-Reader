from math import nan, isnan, inf
from string import ascii_uppercase
from numbers import Number
from warnings import warn

def full_row_iter():
	for letter in ascii_uppercase:
		yield letter
	for letter_1 in ascii_uppercase:
		for letter_2 in ascii_uppercase:
			yield letter_1+letter_2

def row_iter(exhaust_warning=True):
	for label in full_row_iter():
		yield label
		if label == "CU":
			if exhaust_warning:
				warn("Exhausted all possible 99 row labels. Unless you have a plate with exactly 99 rows, this suggests that something went wrong.")
			break

VALID_ROWS = set(row_iter(exhaust_warning=False))

def split_alpha_and_number(name):
	if name=="":
		raise ValueError("Empty name.")
	elif not name.isascii():
		raise ValueError("Not an ASCII name")
	
	for i in range(len(name)+1):
		alpha = name[:i]
		if not alpha.isalpha():
			continue
		
		if name[i:]=="":
			return alpha,nan
		
		if name[i:].isnumeric():
			try:
				number = int(name[i:])
			except ValueError:
				continue
			else:
				return alpha,number
	else:
		raise ValueError("Name does not consist of a string plus (optionally) a number.")

def split_well_name(name):
	try:
		row,col = split_alpha_and_number(name)
	except ValueError:
		raise ValueError("Not a proper well name.")
	
	if not row in VALID_ROWS:
		raise ValueError("Not a proper row identifier.")
	
	if isnan(col):
		raise ValueError("Number is missing")
	
	return row,col

def is_sample_label_string(label):
	if ":" in label:
		label,_,conc_number = label.partition(":")
	
	try:
		name,number = split_alpha_and_number(label)
	except ValueError:
		return False
	
	return isnan(number) or (name not in VALID_ROWS)

def is_sample_id(index):
	if isinstance(index,str):
		return is_sample_label_string(index)
	else:
		try:
			if len(index)!=2:
				return False
		except ValueError:
			return False
		else:
			return is_sample_label_string(index[0]) and isinstance(index[1],Number)

def extract_channel(string,existing_channels):
	name,_,channel = string.partition("[")
	if not channel or channel[-1] != "]":
		raise ValueError
	channel = channel[:-1]
	name = name.rstrip()
	
	if channel.endswith(":Spectrum"):
		channel = channel.partition(":Spectrum")[0]
	
	for ex_channel in existing_channels:
		if (
				   (channel==ex_channel)
				or (isinstance(ex_channel,tuple) and channel==ex_channel[0])
			):
			break
	else:
		raise ValueError
	
	return name,channel

def parse_time(time):
	if time=="?????" or time=="":
		return nan
	else:
		hours, minutes, seconds = map(int,time.split(":"))
		return (hours*60+minutes)*60 + seconds

def parse_number(string):
	if string=="?????" or string=="":
		return nan
	elif string=="OVRFLW":
		return inf
	elif string.startswith("<"):
		float(string[1:])
		return 0
	elif string:
		return float(string)
	else:
		raise ValueError

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

def wrap_variant(func,variant):
	def wrapped(*args,**kwargs):
		return func(*args,variant=variant,**kwargs)
	wrapped.__name__ = func.__name__ + "_" + variant
	return wrapped


