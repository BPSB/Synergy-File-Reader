from synergy_file_reader.tools import split_well_name, extract_channel, parse_time, parse_number, LineBuffer
from math import isnan
from datetime import datetime

format_parsers = [parse_time, parse_number]

class FormatMismatch(Exception): pass
class RepeatingData(Exception): pass

def format_assert(condition):
	if not condition:
		raise FormatMismatch

class SynergyResult(object):
	def __init__(self):
		self.data = {}
		self.rows = []
		self.cols = []
		self.channels = []
		self.results = []
	
	def add_row(self,row):
		if row not in self.rows:
			if self.rows:
				assert len(row)>len(self.rows[-1]) or row>self.rows[-1]
			self.rows.append(row)
	
	def add_col(self,col):
		if col not in self.cols:
			if self.cols:
				assert col > self.cols[-1]
			self.cols.append(col)
	
	def add_channel(self,channel):
		if channel not in self.channels:
			self.channels.append(channel)
	
	def keys(self):
		return self.data.keys()
	
	def convert_index(self,index):
		# Avoid string as single index being interpreted as iterable:
		if isinstance(index,str):
			index = [index]
		else:
			index = list(index)
		
		try:
			row,col = split_well_name(index[0])
			del index[0]
		except ValueError:
			row,col = index[:2]
			del index[:2]
		
		row = row.upper()
		
		if len(index)==0:
			if len(self.channels)==1:
				channel = self.channels[0]
			else:
				raise ValueError("You must specify a channel as there is more than one in this read.")
		elif len(index)==1:
			channel = index[0]
		else:
			raise KeyError("Too many indices.")
		
		return row,col,channel

	def __setitem__(self,index,result):
		row,col,channel = self.convert_index(index)
		self.add_row(row)
		self.add_col(col)
		self.add_channel(channel)
		if (row,col,channel) in self.keys():
			raise RepeatingData
		else:
			self.data[row,col,channel] = result
	
	def __getitem__(self,index):
		return self.data[self.convert_index(index)]


class SynergyRead(SynergyResult):
	def __init__(self):
		super().__init__()
		self.metadata = {}
		self.times = []
		self.temperatures = {}
		self.results = {}
	
	def add_time(self,time):
		if self.times:
			if time != self.times[-1]:
				assert time>self.times[-1]
				self.times.append(time)
		else:
			self.times.append(time)
	
	def add_temperature(self,time,channel,temperature):
		self.add_time(time)
		self.add_channel(channel)
		try:
			self.temperatures[channel].append(temperature)
		except KeyError:
			self.temperatures[channel] = [temperature]
		else:
			assert len(self.temperatures[channel])==len(self.times)
	
	def add_raw_result(self,time,channel,row,col,value):
		self.add_time(time)
		if (row,col,channel) in self.keys():
			self[row,col,channel].append(value)
			assert len(self[row,col,channel])==len(self.times)
		else:
			self[row,col,channel] = [value]
	
	def add_result(self,name,channel,row,col,value):
		if name not in self.results:
			self.results[name] = SynergyResult()
		
		self.results[name][row,col,channel] = value
	
	def add_metadata(self,**metadata):
		if any( key in self.metadata for key in metadata ):
			raise RepeatingData
		
		if "Date" in metadata:
			assert "Time" in metadata
			self.metadata["datetime"] = datetime.strptime(
				metadata.pop("Date") + " " + metadata.pop("Time"),
				"%m/%d/%Y %I:%M:%S %p"
			)
		
		for key,value in metadata.items():
			if key=="Software Version":
				value = tuple( int(x) for x in value.split(".") )
			
			self.metadata[key] = value
	
	# def __repr__(self):
	# 	return(f"SynergyRead( {self.metadata}, {self.times}, {self.temperatures}, {self.raw_data} )")

class SynergyFile(list):
	def __init__(self,filename,encoding="iso-8859-1"):
		super().__init__()
		self.new_read()
		
		with open(filename,"r",encoding=encoding) as f:
			self.line_buffer = LineBuffer(f.read().splitlines())
		
		self.parse_file()
	
	def parse_file(self):
		while self.line_buffer:
			for parser in (
					self.parse_raw_data_columnwise_table,
					self.parse_results_matrix,
					self.parse_procedure,
					self.parse_metadata,
				):
				try:
					parser()
				except FormatMismatch:
					continue
				else:
					break
			else:
				raise ValueError("File does not appear to have a valid or implemented format.")
	
	def new_read(self):
		self.append(SynergyRead())
	
	def parse_metadata(self):
		new_metadata = {}
		for line in self.line_buffer:
			if line == "":
				break
			elif line.count("\t") != 1:
				raise FormatMismatch
			else:
				key,_,value = line.partition("\t")
				if key.endswith(":"):
					key = key[:-1]
				new_metadata[key] = value
		
		self[-1].add_metadata(**new_metadata)
		self.line_buffer.clear()
	
	def parse_procedure(self):
		line_iter = iter(self.line_buffer)
		if next(line_iter)!="Procedure Details" or next(line_iter)!="":
			raise FormatMismatch
		
		procedure = []
		while line:=next(line_iter):
			procedure.append(line)
		self[-1].add_metadata( procedure = "\n".join(procedure) )
		self.line_buffer.clear()
	
	def parse_gain_values(self):
		# TODO
		pass
	
	def parse_results_matrix(self):
		line_iter = iter(self.line_buffer)
		
		format_assert(next(line_iter)=="Results")
		
		try:
			cols = [int(c) for c in next(line_iter).split("\t")[1:]]
		except ValueError:
			raise FormatMismatch
		format_assert( cols==list(range(1,len(cols)+1)) )
		
		results = []
		row = None
		for line in line_iter:
			if line=="":
				break
			new_row,*numbers,name = line.split("\t")
			
			if new_row.isupper() and new_row.isalpha():
				row = new_row
			else:
				format_assert(new_row=="")
			format_assert(row is not None)
			
			for format_parser in format_parsers:
				try:
					numbers = [format_parser(number) for number in numbers]
				except ValueError:
					continue
				else:
					break
			else:
				raise FormatMismatch
			
			results.append((row,numbers,*extract_channel(name)))
		
		for row,numbers,key,channel in results:
			for col,number in zip(cols,numbers):
				self[-1].add_result(key,channel,row,col,number)
		
		self.line_buffer.clear()
	
	def parse_raw_data_columnwise_table(self):
		line_iter = iter(self.line_buffer)
		channel = next(line_iter)
		if "\t" in channel or next(line_iter)!="":
			raise FormatMismatch
		
		fields = next(line_iter).split("\t")
		if len(fields)<3 or fields[0]!="Time" or fields[1]!="T° "+channel:
			raise FormatMismatch
		wells = fields[2:]
		
		results = []
		while line:=next(line_iter):
			time,temperature,*numbers = line.split("\t")
			if len(numbers)!=len(wells):
				raise FormatMismatch
			try:
				result = parse_time(time),parse_number(temperature),*map(parse_number,numbers)
			except ValueError:
				raise FormatMismatch
			results.append(result)
		
		for time,temperature,*numbers in results:
			if time==0 and all(isnan(number) for number in numbers):
				continue
			self[-1].add_temperature(time,channel,temperature)
			for well,number in zip(wells,numbers):
				self[-1].add_raw_result(time,channel,*split_well_name(well),number)
		
		self.line_buffer.clear()


