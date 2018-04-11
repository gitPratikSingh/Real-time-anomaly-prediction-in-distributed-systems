
def cpuLeak():
	# takes up cpu cycles exponentially
	i = 1
	x = 2
	while True:
		for itr in range(i+1):
			x = x*x
		i = 2**i

if __name__ == "__main__":
    cpuLeak()
