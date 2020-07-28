from synergy_file_reader.tools import split_well_name, to_seconds, parse_number, LineBuffer
from math import isnan
from datetime import datetime

class FormatMismatch(Exception): pass
class RepeatingData(Exception): pass

class SynergyRead(object):
	def __init__(self):
		self.metadata = {}
		self.raw_data = {}
		self.times = []
		self.temperatures = {}
		
		self.rows = []
		self.cols = []
		self.channels = []
	
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
	
	def add_result(self,time,channel,row,col,value):
		self.add_time(time)
		self.add_row(row)
		self.add_col(col)
		self.add_channel(channel)
		try:
			self.raw_data[row,col,channel].append(value)
		except KeyError:
			self.raw_data[row,col,channel] = [value]
		else:
			assert len(self.raw_data[row,col,channel])==len(self.times)
	
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
	
	def __getitem__(self,i):
		# Avoid string as single index being interpreted as iterable:
		if isinstance(i,str):
			i = [i]
		else:
			i = list(i)
		
		if i[-1] in self.channels:
			channel = i.pop()
		else:
			if len(self.channels)==1:
				channel = self.channels[0]
			else:
				raise ValueError("You must specify a channel as there is more than one in this read.")
		
		if len(i)==1:
			row,col = split_well_name(i[0])
		else:
			row,col = i
		
		row = row.upper()
		
		return self.raw_data[row,col,channel]
	
	def keys(self):
		return self.raw_data.keys()
	
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
					self.parse_results,
					self.parse_procedure,
					self.parse_metadata,
				):
				try:
					parser()
				except FormatMismatch:
					continue
				else:
					break
	
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
	
	def parse_results(self):
		line_iter = iter(self.line_buffer)
		if next(line_iter)!="Results":
			raise FormatMismatch
		for line in line_iter:
			# TODO
			if line=="":
				break
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
				result = to_seconds(time),parse_number(temperature),*map(parse_number,numbers)
			except ValueError:
				raise FormatMismatch
			results.append(result)
		
		for time,temperature,*numbers in results:
			if time==0 and all(isnan(number) for number in numbers):
				continue
			self[-1].add_temperature(time,channel,temperature)
			for well,number in zip(wells,numbers):
				self[-1].add_result(time,channel,*split_well_name(well),number)
		
		self.line_buffer.clear()


