def bresenham_line(x0, y0, x1, y1):
    """Generate points of a line using Bresenham's line algorithm."""
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

    return points

def draw_ascii_path(width,stations=[(46,14.5,1),(46.5,14.5,255555)]):
    coordinates = open("slo_coordinates.txt", "r").read()
    points = [tuple(map(float, point.split(",")[:2])) for point in coordinates.split()]

    min_lon = min(points, key=lambda t: t[0])[0]
    max_lon = max(points, key=lambda t: t[0])[0]
    min_lat = min(points, key=lambda t: t[1])[1]
    max_lat = max(points, key=lambda t: t[1])[1]

    height = int(width * (max_lat - min_lat) / (max_lon - min_lon))
    canvas = [[' ' for _ in range(width)] for _ in range(height)]

    for i in range(len(points) - 1):
        start = points[i]
        end = points[i+1]
        x0 = int((start[0] - min_lon) / (max_lon - min_lon) * (width - 1))
        y0 = height - 1 - int((start[1] - min_lat) / (max_lat - min_lat) * (height - 1))
        x1 = int((end[0] - min_lon) / (max_lon - min_lon) * (width - 1))
        y1 = height - 1 - int((end[1] - min_lat) / (max_lat - min_lat) * (height - 1))

        line_points = bresenham_line(x0, y0, x1, y1)
        for (x, y) in line_points:
            canvas[y][x] = '*'

    # Plot stations
    for station in stations:
        lat, lon, num = station
        x = int((lon - min_lon) / (max_lon - min_lon) * (width - 1))
        y = height - 1 - int((lat - min_lat) / (max_lat - min_lat) * (height - 1))
        c_count = 0
        for c in str(num):
            canvas[y][x+c_count] = c
            c_count += 1

    for row in canvas:
        print(''.join(row))

#draw_ascii_path(150)
