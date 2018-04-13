import time
def memLeak():
        # takes up memory exponentially
        # adds 1 KB, 2KB, 4kB and so on
        a = []
        i = 2
        while True:
                for x in range(0, i+1):
                        a.append(' ')

                print ("MB:"+ str((float)(len(a))/1024))

                i = i<<1
                time.sleep(1)

if __name__ == "__main__":
    memLeak()
