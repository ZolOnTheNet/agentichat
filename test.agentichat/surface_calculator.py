def calculate_surface(r):
    import math
    return math.pi * (r**2)

if __name__ == '__main__':
    radius = float(input('Entrez le rayon de la surface : '))
    print(calculate_surface(radius))