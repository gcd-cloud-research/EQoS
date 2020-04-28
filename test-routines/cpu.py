

def factorise(num):
    divisors = {}
    while num > 1:
        for i in range(2, num + 1):
            if num % i == 0:
                divisors[i] = divisors[i] + 1 if i in divisors else 1
                num //= i
                break
    return divisors


def dumboperations(num, laps):
    for _ in range(laps):
        num = (num**2)**(1/2)
    return num


if __name__ == '__main__':
    print(dumboperations(123456789.5, 123456789))
