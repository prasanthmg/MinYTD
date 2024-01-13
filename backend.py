import pytube
import http.client
import multiprocessing
import multiprocessing.managers
import shutil
import os
import subprocess
import platform


def check_ffmpeg_exists():
	if platform.system()=='Windows':
		try:
			subprocess.call('ffmpeg', creationflags = subprocess.CREATE_NO_WINDOW)
			return True
		except FileNotFoundError:
			return False
	else:
		try:
			subprocess.call('ffmpeg')
			return True
		except FileNotFoundError:
			return False
			
		
def call_ffmpeg(video_stream, audio_stream, output_stream):
	if platform.system()=='Windows':
		subprocess.call(['ffmpeg', '-i', video_stream, '-i', audio_stream, '-c', 'copy', output_stream], creationflags = subprocess.CREATE_NO_WINDOW)
	else:
		subprocess.call(['ffmpeg', '-i', video_stream, '-i', audio_stream, '-c', 'copy', output_stream])
		
		
class SharedClasses(multiprocessing.managers.BaseManager):
	pass

	
class SharedProgress:
	def __init__(self):
		self.progress = 0
		
	def update_progress(self, progress):
		self.progress = progress
		
	def get_progress(self):
		return self.progress


class SharedCompletionStatus:
	def __init__(self):
		self.is_complete = False
		
	def on_complete(self):
		self.is_complete = True
		
	def get_completion_status(self):
		return self.is_complete


class Task:
	def __init__(self, video_obj, playlist_obj, res, dest, shared_classes_obj):
		self.video_obj = video_obj
		self.playlist_obj = playlist_obj
		self.resolution = res
		self.destination = dest
		self.shared_progress_obj = shared_classes_obj.SharedProgress()
		self.shared_completion_status_obj = shared_classes_obj.SharedCompletionStatus()
		self.process = multiprocessing.Process(target=self.initiate_download)
		self.title = self.video_obj.title if not self.playlist_obj else ('Playlist-'+self.video_obj.title)
		self._is_killed = False
	
	def start(self):
		self.process.start()
	
	def kill(self):
		if self.process.is_alive():
			self.process.terminate()
			self.process.join()
		if not self.is_complete():
			self._is_killed = True	

	def initiate_download(self):
		downloader_obj = TaskDownloader(self.video_obj, self.playlist_obj, self.resolution, self.destination, self.shared_progress_obj, self.shared_completion_status_obj)
		downloader_obj.download()
		
	def get_progress(self):
		return self.shared_progress_obj.get_progress()
		
	def is_killed(self):
		return self._is_killed
		
	def is_complete(self):
		return self.shared_completion_status_obj.get_completion_status()


class YTD:
	def __init__(self):
		self.url = ''
		self.is_valid_url = False
		self.is_playlist_url = False
		self.download_entire_playlist = False
		self.resolution_chosen = ''
		self.destination = ''
		self.resolutions_available = []
		self.video_obj = None
		self.playlist_obj = None
		self.shared_classes_obj = SharedClasses()
		self.shared_classes_obj.register('SharedProgress', SharedProgress)
		self.shared_classes_obj.register('SharedCompletionStatus', SharedCompletionStatus)
		self.shared_classes_obj.start()
		self.url_exception = False
		self.ffmpeg_exists = check_ffmpeg_exists()
	
	def validate_url(self, url):
		self.url = url
		self.url_exception = False
		try:
			self.video_obj = pytube.YouTube(self.url)
			self.is_valid_url = True
			self.resolutions_available = self.get_resolutions()
			try:
				self.playlist_obj = pytube.Playlist(self.url)
				self.is_playlist_url = True
			except (KeyError, http.client.InvalidURL):
				self.is_playlist_url = False
				self.playlist_obj = None
			except:
				self.is_playlist_url = False
				self.playlist_obj = None
				self.url_exception = True							
		except (pytube.exceptions.RegexMatchError, http.client.InvalidURL):
			self.is_valid_url = False
			self.is_playlist_url = False
			self.resolutions_available = []
			self.video_obj = None
			self.playlist_obj = None			
		except:
			self.is_valid_url = False
			self.is_playlist_url = False
			self.resolutions_available = []
			self.video_obj = None
			self.playlist_obj = None
			self.url_exception = True
		if ('list' not in self.url) or ('radio' in self.url):
			self.is_playlist_url = False
			self._playlist_obj = None	
		return self.is_valid_url, self.is_playlist_url, self.resolutions_available 
	
	def get_resolutions(self):
		res_list = []
		streams = self.video_obj.streams if self.ffmpeg_exists else self.video_obj.streams.filter(progressive=True)
		for stream in streams:
			if stream.resolution:
				res_list.append(int(stream.resolution[:-1]))
		res_list = list(set(res_list))
		res_list.sort(reverse=True)
		res_list = [str(x)+'p' for x in res_list]
		return res_list	
		
	def add_task(self):
		task = Task(self.video_obj, self.playlist_obj if self.download_entire_playlist else None, self.resolution_chosen, self.destination, self.shared_classes_obj)
		return task

	
class TaskDownloader:
	def __init__(self, video_obj, playlist_obj, resolution, destination, shared_progress_obj, shared_completion_status_obj):
		self.video_obj = video_obj
		self.playlist_obj = playlist_obj
		self.resolution = resolution
		self.destination = destination
		self.shared_progress_obj = shared_progress_obj
		self.shared_completion_status_obj = shared_completion_status_obj
		self.video_obj.register_on_progress_callback(self.on_progress_callback)
		self.video_stream_size = 0
		self.audio_stream_size = 0
		self.adaptive_audio_download_ongoing = False
		self.tmp_directory = os.path.join(os.getcwd(), 'tmp')
		self.ffmpeg_exists = check_ffmpeg_exists()
		
		os.makedirs(self.tmp_directory, exist_ok=True)
		os.makedirs(self.destination, exist_ok=True)
		
	def download(self):
		if self.playlist_obj:
			self.download_playlist()
		else:
			self.download_video(self.video_obj)
		self.shared_completion_status_obj.on_complete()	
			
	def download_playlist(self):
		video_urls = self.playlist_obj.video_urls
		total = len(video_urls)
		for i,video_url in enumerate(video_urls):
			try:
				yt = pytube.YouTube(video_url)
				if not self.ffmpeg_exists:
					try:
						stream = yt.streams.filter(progressive=True).filter(subtype='mp4').filter(resolution=self.resolution)[0]
					except IndexError:
						stream = yt.streams.filter(progressive=True).filter(subtype='mp4').order_by('resolution')[-1]
					self.download_progressive_stream(stream)
				else:
					self.download_video(yt)
			except:
				pass
			self.update_download_progress(total, total-i-1)
	
	def download_video(self, yt):
		if self.resolution == 'Highest available':
			self.download_highest_resolution_stream(yt)
		else:
			self.download_this_resolution_stream(yt, self.resolution)
			
	def download_highest_resolution_stream(self, yt):
		hrps = self.get_highest_resolution_progressive_stream(yt)
		hras = self.get_highest_resolution_adaptive_stream(yt)
		if self.compare_resolutions(hrps, hras['video']) >= 0:
			self.download_progressive_stream(hrps)
		else:
			self.download_adaptive_stream(hras)
			
	def download_this_resolution_stream(self, yt, res):
		try:
			stream = yt.streams.filter(subtype='mp4').filter(progressive=True).filter(resolution=res)[0]
			self.download_progressive_stream(stream)
		except IndexError:
			try:
				video_stream = yt.streams.filter(type='video').filter(subtype='mp4').filter(adaptive=True).filter(resolution=res)[0]
				audio_stream = yt.streams.filter(type='audio').filter(subtype='mp4').order_by('abr')[-1]	
				stream = {'video':video_stream, 'audio':audio_stream}
				self.download_adaptive_stream(stream)			
			except IndexError:
				self.download_highest_resolution_stream(yt)
				
	def download_progressive_stream(self, st):
		self.video_stream_size = st.filesize
		self.audio_stream_size = 0
		st.download(self.destination, skip_existing=False)
		
	def download_adaptive_stream(self, st):
		self.video_stream_size = st['video'].filesize
		self.audio_stream_size = st['audio'].filesize
		st['video'].download(filename_prefix="video-", output_path=self.tmp_directory, skip_existing=False)
		self.adaptive_audio_download_ongoing = True
		st['audio'].download(filename_prefix="audio-", output_path=self.tmp_directory, skip_existing=False)
		self.adaptive_audio_download_ongoing = False
		video_stream = os.path.join(self.tmp_directory, "video-"+st['video'].default_filename)
		audio_stream = os.path.join(self.tmp_directory, "audio-"+st['audio'].default_filename)
		output_stream = os.path.join(self.tmp_directory, st['video'].default_filename)
		call_ffmpeg(video_stream, audio_stream, output_stream)
		os.remove(video_stream)
		os.remove(audio_stream)
		src_shutil = output_stream
		dest_shutil = os.path.join(self.destination, st['video'].default_filename)
		shutil.move(src_shutil, dest_shutil)

	def on_progress_callback(self, stream, chunk, bytes_remaining):
		total = self.video_stream_size + self.audio_stream_size
		if self.adaptive_audio_download_ongoing:
			remaining = bytes_remaining
		else:
			remaining = self.audio_stream_size + bytes_remaining
		self.update_download_progress(total, remaining)		
	
	def update_download_progress(self, total, remaining):
		percentage_completed = ((total-remaining)/total) * 100
		self.shared_progress_obj.update_progress(percentage_completed)
	
	def compare_resolutions(self, st1, st2):
		return (int(st1.resolution[:-1])-(int(st2.resolution[:-1])))
	
	def get_highest_resolution_progressive_stream(self, yt):
		return yt.streams.filter(subtype='mp4').filter(progressive=True).order_by('resolution')[-1]
	
	def get_highest_resolution_adaptive_stream(self, yt):
		video_stream = yt.streams.filter(type="video").filter(adaptive=True).filter(subtype='mp4').order_by('resolution')[-1]
		audio_stream = yt.streams.filter(type="audio").filter(subtype='mp4').order_by('abr')[-1]
		hras = {'video':video_stream, 'audio':audio_stream}
		return hras		
	

	

		

			

		

