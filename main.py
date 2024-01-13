import frontend
import backend
from multiprocessing import freeze_support

if __name__ ==  '__main__':
	freeze_support()
	backend_obj = backend.YTD()
	frontend_obj = frontend.YTD(backend_obj)
	frontend_obj.run()
