import csv

class TrackBounds:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key in ['TRACK']:
                value = int(value)
            elif key in ['DIRECTION', 'TRACK_NAME']:
                value = str(value)
            else:
                value = float(value)
            setattr(self, key, value)

def load_track_bounds(filename):
    try:
        with open(filename, 'r') as f:
            rows = list(csv.DictReader(f))
        return [TrackBounds(**row) for row in rows]
    except Exception as e:
        print(f"Error loading track bounds: {e}")
        return []

def line_intersects(p0_x, p0_y, p1_x, p1_y, p2_x, p2_y, p3_x, p3_y):
    s1_x = p1_x - p0_x
    s1_y = p1_y - p0_y
    s2_x = p3_x - p2_x
    s2_y = p3_y - p2_y

    denom = (-s2_x * s1_y + s1_x * s2_y)
    if denom == 0:
        return (0, '??')

    s = (-s1_y * (p0_x - p2_x) + s1_x * (p0_y - p2_y)) / denom
    t = (s2_x * (p0_y - p2_y) - s2_y * (p0_x - p2_x)) / denom

    d = '--'
    if s2_x > 0: d = 'PX'
    elif s2_x < 0: d = 'NX'
    elif s2_y > 0: d = 'PY'
    elif s2_y < 0: d = 'NY'
    else: d = '??'

    if s >= 0 and s <= 1 and t >= 0 and t <= 1:
        return (1, d)
    return (0, d)

def get_bounding_box(x1, y1, x2, y2):
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

def get_bounding_box_area(box):
    return (box[2] - box[0]) * (box[3] - box[1])

def get_bounding_box_intersection(box1, box2):
    left = max(box1[0], box2[0])
    right = min(box1[2], box2[2])
    top = max(box1[1], box2[1])
    bottom = min(box1[3], box2[3])
    if left > right or top > bottom:
        return None
    return left, top, right, bottom

def calculate_iou(outer_bounding_box, inner_bounding_box):
    intersection = get_bounding_box_intersection(outer_bounding_box, inner_bounding_box)
    if intersection is None:
        return 0
    intersection_area = get_bounding_box_area(intersection)
    outer_area = get_bounding_box_area(outer_bounding_box)
    inner_area = get_bounding_box_area(inner_bounding_box)
    iou = intersection_area / (outer_area + inner_area - intersection_area)
    return iou

class TrackDetector:
    def __init__(self, csv_path="gt7trackdetect.csv"):
        self.track_bounds = load_track_bounds(csv_path)
        self.reset()

    def reset(self):
        self.minX = 999999.9
        self.minY = 999999.9
        self.maxX = -999999.9
        self.maxY = -999999.9
        self.oldXYZ = None

    def update_bounds(self, x, z):
        if x > self.maxX: self.maxX = x
        if x < self.minX: self.minX = x
        if z > self.maxY: self.maxY = z
        if z < self.minY: self.minY = z

    def detect_track(self, x, z):
        if self.oldXYZ is None:
            self.oldXYZ = [x, z]
            return None

        newXYZ = [x, z]
        matches = self._find_matching_track(self.oldXYZ[0], self.oldXYZ[1], newXYZ[0], newXYZ[1])
        
        self.oldXYZ = newXYZ
        
        if matches and len(matches) == 1:
            match = matches[0]
            probability = match[0]
            track_id = match[1]
            if probability > 0.96:
                return track_id
        return None

    def _find_matching_track(self, L1X, L1Y, L2X, L2Y, max_matches=3, min_iou=0.02):
        outer_bounding_box = get_bounding_box(self.minX, self.minY, self.maxX, self.maxY)
        matches = []
        for element in self.track_bounds:
            inner_bounding_box = get_bounding_box(element.MINX, element.MINY, element.MAXX, element.MAXY)
            intersects, direction = line_intersects(element.P1X, element.P1Y, element.P2X, element.P2Y, L1X, L1Y, L2X, L2Y)
            if intersects == 0 or element.DIRECTION != direction:
                continue
            iou = calculate_iou(outer_bounding_box, inner_bounding_box)
            matches.append((iou, element.TRACK))

        matches.sort(key=lambda x: x[0], reverse=True)
        if not matches:
            return None

        best_match = matches[0]
        filtered_matches = [m for m in matches if m[0] >= best_match[0] * (1 - min_iou)]
        return filtered_matches[:max_matches]
