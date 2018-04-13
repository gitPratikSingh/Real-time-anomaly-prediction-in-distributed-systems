import time

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
                        break


if __name__ == "__main__":
        cpuLeak()
