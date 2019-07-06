import random
import time

# generate n random numbers for sampling
def get_random(rcount_, total_):
    def gen_random():
        while True:
            yield random.randrange(1, total_+1, 1)

    def gen_n_unique(source, n__):
        seen = set()
        seenadd = seen.add
        for i in (i for i in source() if i not in seen and not seenadd(i)):
            yield i
            if len(seen) == n__:
                break

    return [i for i in gen_n_unique(gen_random, min(rcount_, int(total_)))]


t = time.time()
rands = get_random(100000, 100000)
print(rands)
print(len(rands))
print(time.time() - t)