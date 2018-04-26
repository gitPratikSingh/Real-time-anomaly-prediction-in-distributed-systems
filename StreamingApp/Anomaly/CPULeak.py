import time
import threading

def cpuLeak():
		# takes up cpu cycles incrementally
		# 1s, it first uses the CPU for 1%, 2%,... 100%
		percent = 1
		while True:
			ss = (int)(time.time())*1000
			es = ss + 1000
			x=2
			percent = percent + 1
			esCpu = ss + (float)(percent*10)

			print("compute Step"+str(percent))
			print(ss)
			print(esCpu)

			# compute for percent fraction of CPU
			while (time.time()*1000) < esCpu:
				x=x*2

			#sleep for the remaining time
			sltime = (float)(es - (int)(time.time()*1000))/1000
			print(sltime)
			time.sleep(sltime)

			if(percent==100):
				while 1:
					x=x*2


if __name__ == "__main__":
	try:
		print("In main")
		for th in range(10):
			thread_first = threading.Thread(target=cpuLeak)
			thread_first.daemon = True
			thread_first.start()
        
		thread_first.join()
	
	except KeyboardInterrupt:
		sys.exit(0)

			
		
