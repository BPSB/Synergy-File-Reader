from synergy_file_reader.tools import split_well_name, to_seconds, parse_number, LineBuffer
from math import isnan

class FormatMismatch(Exception): pass
class RepeatingData(Exception): pass

class SynergyRead(object):
	def __init__(self):
		self.metadata = {}
		self.raw_data = {}
		self.times = []
		self.temperatures = {}
	
	def add_time(self,time):
		if self.times:
			if time != self.times[-1]:
				assert time>self.times[-1]
				self.times.append(time)
		else:
			self.times.append(time)
	
	def add_temperature(self,time,channel,temperature):
		self.add_time(time)
		try:
			self.temperatures[channel].append(temperature)
		except KeyError:
			self.temperatures[channel] = [temperature]
		else:
			assert len(self.temperatures[channel])==len(self.times)
	
	def add_result(self,time,channel,row,col,value):
		self.add_time(time)
		try:
			self.raw_data[row,col,channel].append(value)
		except KeyError:
			self.raw_data[row,col,channel] = [value]
		else:
			assert len(self.raw_data[row,col,channel])==len(self.times)
	
	def __getitem__(self,i):
		if len(i)==2:
			row,col = split_well_name(i[0])
			channel = i[1]
		else:
			row,col,channel = i
		
		return self.raw_data[row,col,channel]
	
	def keys(self):
		return self.raw_data.keys()
	
	@property
	def rows(self):
		pass
	
	def __repr__(self):
		return(f"SynergyRead( {self.metadata}, {self.times}, {self.temperatures}, {self.raw_data} )")

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
					self.parse_raw_data_1,
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
		
		self.add_metadata(**new_metadata)
		self.line_buffer.clear()
	
	def add_metadata(self,**metadata):
		if any( key in self[-1].metadata for key in metadata ):
			raise RepeatingData
		
		for key,value in metadata.items():
			if key=="Software Version":
				value = tuple( int(x) for x in value.split(".") )
			
			self[-1].metadata[key] = value
	
	def parse_procedure(self):
		line_iter = iter(self.line_buffer)
		if next(line_iter)!="Procedure Details" or next(line_iter)!="":
			raise FormatMismatch
		
		procedure = []
		while line:=next(line_iter):
			procedure.append(line)
		self.add_metadata( procedure = "\n".join(procedure) )
		self.line_buffer.clear()
	
	def parse_gain_values(self):
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
	
	def parse_raw_data_1(self):
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
			if line=="":
				break
			
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


