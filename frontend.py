import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import threading


APP_NAME = 'MinYTD'


def spinning_cursor():
	while(1):
		for c in '|/-\\':
			yield c
				

class Task:
	def __init__(self, backend_obj):
		self.WINDOW_TITLE = APP_NAME
		self.WINDOW_MINIMUM_HEIGHT = 0
		self.WINDOW_MINIMUM_WIDTH = 250
		self.FRAME_INTERNAL_PADDING = {'x':2, 'y':2}
		self.WIDGET_EXTERNAL_PADDING = {'x':2, 'y':1}
		
		self.backend_obj = backend_obj
		self.title = backend_obj.title
		self._is_killed = False

		self.window = tk.Toplevel()
		self.window.title(self.WINDOW_TITLE)
		self.window.minsize(self.WINDOW_MINIMUM_WIDTH, self.WINDOW_MINIMUM_HEIGHT)
		self.window.protocol('WM_DELETE_WINDOW', self.on_close)
		self.window.resizable(0,0)
		
		self.frame = tk.Frame(self.window)
		self.frame.config(padx=self.FRAME_INTERNAL_PADDING['x'], pady=self.FRAME_INTERNAL_PADDING['y'])
		
		self.title_lbl = tk.Label(self.frame, text=self.title)
		self.progressbar = ttk.Progressbar(self.frame, orient=tk.HORIZONTAL)
		
		self.download_status_lbl = tk.Label(self.frame)

		self.packer()
		
	def packer(self):
		self.frame.pack(expand=True, fill=tk.BOTH)		
		self.title_lbl.pack(padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		self.progressbar.pack(expand=True, fill=tk.X, padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		self.download_status_lbl.pack(side=tk.LEFT)
		
	def start(self):
		self.backend_obj.start()
		self.update_progressbar()
		
	def kill(self):
		if not self.is_complete():
			self.backend_obj.kill()
		self._is_killed = True
		self.window.destroy()

	def is_killed(self):
		return self._is_killed
		
	def is_complete(self):
		return self.backend_obj.is_complete()
		
	def on_close(self):
		self.kill()
	
	def update_progressbar(self):
		if not self.is_complete():
			self.progressbar['value'] = self.backend_obj.get_progress()
			self.download_status_lbl['text'] = 'Downloading.. ' + '{:.2f}'.format(self.backend_obj.get_progress()).rstrip('0').rstrip('.') + '%'
			self.window.after(100, self.update_progressbar)
		else:
			self.progressbar['value'] = 100
			self.download_status_lbl['text'] = 'Download Complete.'
			

class YTD:
	def __init__(self, backend_obj):
		self.ROOT_WINDOW_ICON_FILE = 'icon.png'
		self.ROOT_WINDOW_MINIMUM_WIDTH = 400
		self.ROOT_WINDOW_MINIMUM_HEIGHT = 170
		self.URL_ENTRY_DEFAULT_TXT = 'Enter URL'
		self.PLAYLIST_CHECKBTN_TXT = 'download entire playlist'
		self.RESOLUTION_LBL_TXT = 'Resolution'
		self.DESTINATION_LBL_TXT = 'Destination'
		self.BROWSE_BTN_TXT = 'Browse'
		self.DOWNLOAD_BTN_TXT = 'DOWNLOAD'
		self.APP_FRAME_INTERNAL_PADDING = {'x':5, 'y':5}
		self.FRAME_INTERNAL_PADDING = {'x':2, 'y':2}
		self.WIDGET_EXTERNAL_PADDING = {'x':1, 'y':1}
		
		self.backend_obj = backend_obj
		if self.backend_obj.ffmpeg_exists:
			self.resolution_list_default = ['Highest available', '2160p', '1440p', '1080p', '720p', '480p', '360p', '144p']
		else:
			self.resolution_list_default = ['720p', '480p', '360p', '144p']
		self.tasks = []
		
			#create and configure root window
		self.root = tk.Tk()
		self.root.title(APP_NAME)
		self.root_window_icon = tk.PhotoImage(file=self.ROOT_WINDOW_ICON_FILE)
		self.root.iconphoto(True, self.root_window_icon)
		self.root.minsize(self.ROOT_WINDOW_MINIMUM_WIDTH, self.ROOT_WINDOW_MINIMUM_HEIGHT)
		self.root.resizable(0,0)
		self.root.rowconfigure(0, weight=1)
		self.root.columnconfigure(0, weight=1)			
		#Tk()variables to track user input on GUI
		self.url_entry_value = tk.StringVar()
		self.playlist_checkbtn_value = tk.IntVar()
		self.resolution_option_value = tk.StringVar()
		self.destination_entry_value = tk.StringVar()
		#variable to track status of url input by user
		self.url_status = {
		'is_valid'   : False, 
		'is_playlist': False,
		'resolutions': []
		}
		
			#create and configure root window widgets
		#application frame
		self.app_frame = tk.Frame(self.root)
		self.app_frame.config(padx=self.APP_FRAME_INTERNAL_PADDING['x'], pady=self.APP_FRAME_INTERNAL_PADDING['y'])
		self.app_frame.columnconfigure(0, weight=1)
		self.app_frame.rowconfigure([0,1,2,3], weight=0)
		
			#create and configure application frame widgets
		#url entry frame
		self.url_frame = tk.Frame(self.app_frame)
		self.url_frame.config(padx=self.FRAME_INTERNAL_PADDING['x'], pady=self.FRAME_INTERNAL_PADDING['y'])
		self.url_frame.columnconfigure(0, weight=1)
		self.url_frame.rowconfigure([0,1], weight=0)	
		#resolution choice frame
		self.resolution_frame = tk.Frame(self.app_frame)
		self.resolution_frame.config(padx=self.FRAME_INTERNAL_PADDING['x'], pady=self.FRAME_INTERNAL_PADDING['y'])
		#destination frame
		self.destination_frame = tk.Frame(self.app_frame)
		self.destination_frame.config(padx=self.FRAME_INTERNAL_PADDING['x'], pady=self.FRAME_INTERNAL_PADDING['y'])
		self.destination_frame.columnconfigure(1, weight=1)
		#download button frame
		self.download_frame = tk.Frame(self.app_frame)
		self.download_frame.config(padx=self.FRAME_INTERNAL_PADDING['x'], pady=self.FRAME_INTERNAL_PADDING['y'])
		
			#create and configure url entry frame widgets
		#url entry 
		self.url_entry = tk.Entry(self.url_frame, textvariable=self.url_entry_value)
		#url entry right click menu
		self.url_entry_right_clk_menu = tk.Menu(self.root, tearoff=0)
		self.url_entry_right_clk_menu.add_command(label='Paste', command=lambda: self.url_entry.event_generate('<<Paste>>'))
		#playlist checkbutton
		self.playlist_checkbtn = tk.Checkbutton(self.url_frame, text=self.PLAYLIST_CHECKBTN_TXT, variable=self.playlist_checkbtn_value, onvalue=1, offvalue=0)
		
			#create and configure resolution frame widgets
		#resolution label
		self.resolution_lbl = tk.Label(self.resolution_frame, text=self.RESOLUTION_LBL_TXT)
		#resolution dropdown
		self.resolution_dropdwn = tk.OptionMenu(self.resolution_frame, self.resolution_option_value, None)
		#resolution loading label
		self.resolution_loading_lbl = tk.Label(self.resolution_frame, text='')
		
			#create and configure detination frame widgets
		#destination label
		self.destination_lbl = tk.Label(self.destination_frame, text=self.DESTINATION_LBL_TXT)
		#destination entry
		self.destination_entry = tk.Entry(self.destination_frame, textvariable=self.destination_entry_value)
		#browse button
		self.browse_btn = tk.Button(self.destination_frame, text=self.BROWSE_BTN_TXT)
		
			#create and configure download frame widgets
		#download button
		self.download_btn = tk.Button(self.download_frame, text=self.DOWNLOAD_BTN_TXT)
			
			#pack widgets
		self.packer()
		
	def packer(self):
		#packing into root
		self.app_frame.grid(row=0, column=0, sticky='nsew')
		#packing into application frame
		self.url_frame.grid(row=0, column=0, sticky='nsew')
		self.resolution_frame.grid(row=1, column=0, sticky='nsew')
		self.destination_frame.grid(row=2, column=0, sticky='nsew')
		self.download_frame.grid(row=3, column=0, sticky='nsew')
		#packing into url frame
		self.url_entry.grid(row=0, column=0, sticky='ew', padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		self.playlist_checkbtn.grid(row=1, column=0, sticky='w', padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		#packing into resolution frame
		self.resolution_lbl.pack(side=tk.LEFT, padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		self.resolution_dropdwn.pack(side=tk.LEFT, padx=5+self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		self.resolution_loading_lbl.pack(side=tk.LEFT)
		#packing into destination frame
		self.destination_lbl.grid(row=0, column=0, sticky='w', padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		self.destination_entry.grid(row=0, column=1, sticky='ew', padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		self.browse_btn.grid(row=0, column=2, sticky='w', padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		#packing into destination frame
		self.download_btn.pack(padx=self.WIDGET_EXTERNAL_PADDING['x'], pady=self.WIDGET_EXTERNAL_PADDING['y'])
		
	def initialise(self): 
		#url entry
		self.url_entry_value.set(self.URL_ENTRY_DEFAULT_TXT)
		self.url_entry.config(fg='grey')
		self.url_entry_default_on = True
		#playlist checkbutton
		self.playlist_checkbtn_value.set(0)
		self.playlist_checkbtn.config(state=tk.DISABLED)
		self.playlist_checkbtn_enabled = False
		#resolution dropdown
		self.resolution_option_value.set('')
		self.resolution_dropdwn.config(state=tk.DISABLED)
		#destination entry
		self.destination_entry_value.set('')
		self.destination_entry.config(state=tk.DISABLED)
		
	def bind_event_handlers(self):
		#event handlers
		self.url_entry.bind('<FocusIn>', self.handle_url_entry_focus_in)
		self.url_entry.bind('<FocusOut>', self.handle_url_entry_focus_out)
		self.url_entry.bind('<<Paste>>', self.handle_url_entry_paste)
		self.url_entry.bind('<Button-3><ButtonRelease-3>', self.handle_url_entry_right_clk)
		#commands
		self.playlist_checkbtn.config(command=self.command_playlist_checkbtn)
		self.browse_btn.config(command=self.command_browse_btn)
		self.download_btn.config(command=self.command_download_btn)
		#protocols
		self.root.protocol("WM_DELETE_WINDOW", self.on_close)
		#tracers
		self.url_entry_value.trace('w', self.tracer_url_entry_value)
		self.resolution_option_value.trace('w', self.tracer_resolution_option_value)
		self.destination_entry_value.trace('w', self.tracer_destination_entry_value)
		
	def run(self):
		self.initialise()
		self.bind_event_handlers()
		if not self.backend_obj.ffmpeg_exists:
				self.root.after(500, self.display_ffmpeg_not_exist_msgbox)
		self.root.mainloop()
	
	#------------------event handlers-----------------------------------------#
	
	#event handlers				
	def handle_url_entry_focus_in(self,_):
		if self.url_entry_default_on:
			self.url_entry.delete(0, tk.END)
			self.url_entry.config(fg='black')
			self.url_entry_default_on = False
		self.url_entry.select_range(0, tk.END)
		
	def handle_url_entry_focus_out(self,_):
		if not self.url_entry_default_on:
			if not self.url_entry.get():
				self.url_entry.config(fg='grey')
				self.url_entry.insert(0, self.URL_ENTRY_DEFAULT_TXT)
				self.url_entry_default_on = True
	
	def handle_url_entry_paste(self,_):
		try:
			self.url_entry.delete('sel.first', 'sel.last')
		except:
			pass
			
	def handle_url_entry_right_clk(self, event):
		if self.url_entry_default_on:
			self.url_entry.delete(0, tk.END)
			self.url_entry.config(fg='black')
			self.url_entry_default_on = False
		self.url_entry_right_clk_menu.tk_popup(event.x_root, event.y_root)
		
			
	#commands		
	def command_playlist_checkbtn(self):
		if self.playlist_checkbtn_value.get():
			self.enable_and_populate_resolution_dropdwn(self.resolution_list_default)
		else:
			self.enable_and_populate_resolution_dropdwn(self.url_status['resolutions'])
		self.backend_obj.download_entire_playlist = self.playlist_checkbtn_value.get()
			
	def command_browse_btn(self):
		self.destination_entry_value.set(filedialog.askdirectory())
		
	def command_download_btn(self):
		if self.url_status['is_valid']:
			if self.destination_entry_value.get():
				task = Task(self.backend_obj.add_task())
				self.tasks.append(task)
				task.start()
			else:
				messagebox.showerror("Error", "Please select a destination folder")
		else:
			messagebox.showerror("Error", "Please enter a valid URL")
			
	#protocols
	def on_close(self):
		if messagebox.askokcancel("Quit", "Do you want to quit?\n(This will cancel all ongoing downloads, if any)"):
			for task in self.tasks:
				task.kill()
			self.root.destroy()	
		
	#tracers		
	def tracer_url_entry_value(self, *_):
		t = threading.Thread(target=self.backend_obj.validate_url, args=(self.url_entry_value.get(),))
		t.start()
		self.on_url_validating(t)

		
	def tracer_resolution_option_value(self, *_):
		self.backend_obj.resolution_chosen =  self.resolution_option_value.get()
		
	def tracer_destination_entry_value(self, *_):
		self.backend_obj.destination = self.destination_entry_value.get()
	
	#helpers		
	def enable_playlist_checkbtn(self):		
		self.playlist_checkbtn.config(state=tk.NORMAL)
		self.playlist_checkbtn_enabled = True
		self.backend_obj.download_entire_playlist = self.playlist_checkbtn_value.get()
		
	def disable_playlist_checkbtn(self):
		self.playlist_checkbtn.config(state=tk.DISABLED)
		self.playlist_checkbtn_enabled =False
		self.backend_obj.download_entire_playlist = False
		
	def enable_resolution_dropdwn(self):
		self.resolution_dropdwn.config(state=tk.NORMAL)

	def disable_resolution_dropdwn(self):
		self.resolution_option_value.set('')
		self.resolution_dropdwn.config(state=tk.DISABLED)
		
	def enable_and_populate_resolution_dropdwn(self, lst):
		self.resolution_option_value.set(lst[0])
		self.enable_resolution_dropdwn()
		self.resolution_dropdwn['menu'].delete(0, tk.END)
		for x in lst:
			self.resolution_dropdwn['menu'].add_command(label=x, command=tk._setit(self.resolution_option_value, x))

	def display_ffmpeg_not_exist_msgbox(self):
		messagebox.showinfo(APP_NAME, 'Your system does not contain FFmpeg.\nInstall FFmpeg to download high quality videos(1080p and above)')
	
	def on_url_validating(self, thread, cursor=None):
		if not cursor:
			cursor = spinning_cursor()
		if thread.is_alive():
			self.resolution_loading_lbl['text'] = next(cursor)
			self.root.after(50, self.on_url_validating, thread, cursor)
		else:
			self.resolution_loading_lbl['text'] = ''
			self.on_url_validating_finish()

	def on_url_validating_finish(self):
		self.url_status['is_valid'] = self.backend_obj.is_valid_url
		self.url_status['is_playlist'] = self.backend_obj.is_playlist_url
		self.url_status['resolutions'] = self.backend_obj.resolutions_available
		if self.url_status['is_valid']:
			if self.url_status['is_playlist']:
				self.enable_playlist_checkbtn()
			else:
				self.disable_playlist_checkbtn()
			if self.playlist_checkbtn_value.get() and self.playlist_checkbtn_enabled:
				self.enable_and_populate_resolution_dropdwn(self.resolution_list_default)
			else:
				self.enable_and_populate_resolution_dropdwn(self.url_status['resolutions'])
		elif self.backend_obj.url_exception:
			self.disable_playlist_checkbtn()
			self.disable_resolution_dropdwn()
			messagebox.showerror("Error", "This URL cannot be downloaded now.\nPlease try again later.")
		else:
			self.disable_playlist_checkbtn()
			self.disable_resolution_dropdwn()

