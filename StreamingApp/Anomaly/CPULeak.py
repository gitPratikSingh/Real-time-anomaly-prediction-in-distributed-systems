import time

def cpuLeak():
	# takes up cpu cycles incrementally
	# 1s, it first uses the CPU for 1%, 2%,... 100%
	percent = 1
	while True:
		sms = (int)time.time()
		ems = sms + 1000
		x=2
		percent = percent + 1
		emsCpu = sms + 10*percent
		
		# compute for percent fraction of CPU
		while (int)time.time() < emsCpu:
			x=x*2
			
		#sleep for the remaining time 
		time.sleep((ems - (int)time.time())/1000)

	
if __name__ == "__main__":
    cpuLeak()
